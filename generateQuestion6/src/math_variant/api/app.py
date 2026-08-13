"""API 계층 (P6) — 교사 검토 화면용 FastAPI 엔드포인트.

- GET  /api/runs/{run_id}              → 검증(PASS)·필수 산출물을 갖춘 후보만 반환
- POST /api/runs/{run_id}/candidates/{candidate_id}/decision → 승인/반려

게이트:
- 반려는 reject_reason_code 필수.
- 이미 결정된 후보는 중복 이벤트를 만들지 않고 기존 결정을 반환(멱등).
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal, Protocol

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from math_variant.api.adapters import report_to_run_store
from math_variant.api.jobs import CreateOptions, JobStore
from math_variant.api.problems import ProblemStore
from math_variant.api.storage import (
    CandidateNotFoundError,
    RunNotFoundError,
    RunStore,
)
from math_variant.events import PipelineEvent


def _recover_stale_jobs() -> None:
    """재시작 시 queued/running 으로 남은 작업을 실패로 처리한다 (중단 복구)."""
    jobs_store = _default_jobs()
    for job in jobs_store.list_jobs():
        if job.status in {"queued", "running"}:
            jobs_store.fail(job.job_id, "서버 재시작으로 작업이 중단되었다", "JOB_INTERRUPTED")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    _recover_stale_jobs()
    yield


app = FastAPI(
    title="수학문제 변형기 API",
    version="0.1.0",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

_store: RunStore | None = None


def _default_store() -> RunStore:
    global _store
    if _store is None:
        _store = RunStore(Path("runs"))
    return _store


class Runner(Protocol):
    """백그라운드 생성 작업 실행자 계약 (테스트에서 fake 로 대체)."""

    def start(self, job_id: str, source_text: str, options: dict[str, Any]) -> None: ...


_jobs: JobStore | None = None
_problems: ProblemStore | None = None
_runner: Runner | None = None
_active_job_id: str | None = None
_active_job_lock = threading.Lock()

# LLM 토큰 델타 버퍼: llm_delta 이벤트는 영속화하지 않고 메모리에만 둔다.
# (토큰 단위라 많고, 완료된 llm_call 이벤트가 요약을 남기므로 디스크에 남길 필요가 없다)
_delta_buffers: dict[str, list[PipelineEvent]] = {}
_delta_lock = threading.Lock()


def _default_jobs() -> JobStore:
    global _jobs
    if _jobs is None:
        _jobs = JobStore(Path("data/jobs"))
    return _jobs


def _default_problems() -> ProblemStore:
    global _problems
    if _problems is None:
        _problems = ProblemStore(Path("data/problems"))
    return _problems


def _default_runner() -> Runner:
    global _runner
    if _runner is None:
        _runner = PipelineRunner(_default_jobs(), _default_store())
    return _runner


def _reset_active_job() -> None:
    global _active_job_id
    _active_job_id = None


class PipelineRunner:
    """JobStore 에 이벤트를 기록하면서 파이프라인을 백그라운드로 실행한다."""

    def __init__(
        self,
        jobs: JobStore,
        store: RunStore,
        sandbox_image: str = "math-variant-sandbox:test",
    ) -> None:
        self.jobs = jobs
        self.store = store
        self.sandbox_image = sandbox_image

    def start(self, job_id: str, source_text: str, options: dict[str, Any]) -> None:
        thread = threading.Thread(
            target=self._execute,
            args=(job_id, source_text, options),
            daemon=True,
        )
        thread.start()

    def _execute(self, job_id: str, source_text: str, options: dict[str, Any]) -> None:
        from math_variant.errors import MathVariantError
        from math_variant.pipeline_factory import build_agent_pipeline
        from math_variant.services.normalize import normalize_source

        def _on_event(event: PipelineEvent) -> None:
            if event.type == "llm_delta":
                with _delta_lock:
                    _delta_buffers.setdefault(job_id, []).append(event)
                return
            self.jobs.append_event(job_id, event)

        try:
            self.jobs.set_status(job_id, "running")
            pipeline = build_agent_pipeline(
                ideator_count=int(options.get("ideator_count", 3)),
                max_refine=int(options.get("max_refine", 2)),
                on_event=_on_event,
                runs_dir=Path("runs") / "artifacts" / job_id,
                figures_dir=Path("runs") / "artifacts" / job_id / "figures",
                sandbox_image=self.sandbox_image,
            )
            report = pipeline.run(
                normalize_source(source_text),
                difficulty_target=str(options.get("difficulty_target", "")),
            )
        except MathVariantError as exc:
            self.jobs.fail(job_id, exc.error.message, exc.code.value)
        except Exception as exc:  # 러너에서 어떤 실패도 job 에 남긴다
            from math_variant.providers.structured import redact_secrets

            self.jobs.fail(job_id, redact_secrets(str(exc))[:500])
        else:
            run_data = report_to_run_store(report)
            run_data["run_id"] = job_id
            try:
                job = self.jobs.load(job_id)
                run_data["source"] = job.source
            except ValueError:
                pass
            self.store.save_run(job_id, run_data)
            self.jobs.complete(job_id, {"run_id": job_id, "candidates": len(report.candidates)})
        finally:
            _clear_active(job_id)
            with _delta_lock:
                _delta_buffers.pop(job_id, None)


def _try_acquire_active() -> bool:
    global _active_job_id
    with _active_job_lock:
        if _active_job_id is not None:
            return False
        _active_job_id = "pending"
        return True


def _set_active(job_id: str) -> None:
    global _active_job_id
    with _active_job_lock:
        _active_job_id = job_id


def _clear_active(job_id: str) -> None:
    global _active_job_id
    with _active_job_lock:
        if _active_job_id == job_id:
            _active_job_id = None


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(approved|rejected)$")
    reject_reason_code: str | None = None


class SourcePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["text", "problem"] = "text"
    text: str | None = None
    problem_id: str | None = None


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: SourcePayload
    options: CreateOptions = Field(default_factory=CreateOptions)


class ProblemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    title: str = ""
    source: Literal["manual", "approved"] = "manual"
    source_run_id: str | None = None


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"status": "ok"}


@app.get("/api/runs")
def list_runs() -> list[dict[str, Any]]:
    return _default_store().list_runs()


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    try:
        data = _default_store().public_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # 옛 실행(run 데이터에 source 가 없던 시기)은 생성 작업에서 원문을 보충한다.
    if not data.get("source"):
        try:
            job = _default_jobs().load(run_id)
            data["source"] = job.source
        except ValueError:
            pass
    return data


@app.post("/api/runs/{run_id}/candidates/{candidate_id}/decision")
def decide(
    run_id: str,
    candidate_id: str,
    payload: DecisionRequest,
    response: Response,
    bypass_reason_check: bool = Query(default=False, include_in_schema=False),
) -> dict[str, Any]:
    if (
        payload.decision == "rejected"
        and not payload.reject_reason_code
        and not bypass_reason_check
    ):
        raise HTTPException(
            status_code=422,
            detail="반려 사유(reject_reason_code)가 필요하다",
        )
    try:
        event = _default_store().apply_decision(
            run_id, candidate_id, payload.decision, payload.reject_reason_code
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CandidateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if payload.decision == "approved":
        try:
            run_data = _default_store().load_run(run_id)
        except RunNotFoundError:
            run_data = {}
        candidate_data = next(
            (c for c in run_data.get("candidates", []) if c.get("candidate_id") == candidate_id),
            None,
        )
        if candidate_data and candidate_data.get("problem_text"):
            try:
                _default_problems().register(
                    candidate_data["problem_text"],
                    title=f"{run_id} {candidate_id}",
                    source="approved",
                    source_run_id=run_id,
                )
            except ValueError:
                pass  # 공백 텍스트 등록 실패는 무시
    response.status_code = 201
    return event


@app.post("/api/generations")
def create_generation(payload: GenerationRequest) -> dict[str, Any]:
    source = payload.source
    if source.mode == "text":
        text = (source.text or "").strip()
        if not text:
            raise HTTPException(status_code=422, detail="원문제 텍스트가 필요하다")
        label = ""
    else:
        try:
            problem = _default_problems().get(source.problem_id or "")
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        text = problem.text
        label = problem.title or problem.problem_id
    if not _try_acquire_active():
        raise HTTPException(status_code=409, detail="다른 생성 작업이 실행 중이다")
    options = payload.options
    try:
        job = _default_jobs().create(text, options, source_mode=source.mode, source_label=label)
    except Exception:
        _clear_active("pending")
        raise
    try:
        _set_active(job.job_id)
        _default_runner().start(job.job_id, text, options.model_dump())
    except Exception:
        _clear_active(job.job_id)
        raise
    return {"job_id": job.job_id, "run_id": job.run_id, "status": job.status}


@app.get("/api/generations/{job_id}")
def get_generation(job_id: str) -> dict[str, Any]:
    try:
        return _default_jobs().load(job_id).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/generations/{job_id}/events")
def stream_generation_events(job_id: str) -> StreamingResponse:
    try:
        _default_jobs().load(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def event_source() -> AsyncIterator[str]:
        last_index = 0
        delta_index = 0
        while True:
            current = _default_jobs().load(job_id)
            events = current.events
            while last_index < len(events):
                event = events[last_index]
                yield f"data: {event.model_dump_json()}\n\n"
                last_index += 1
            # 영속 이벤트 이후에 도착한 스트리밍 델타를 순서대로 이어서 전송한다.
            with _delta_lock:
                deltas = list(_delta_buffers.get(job_id, ()))
            while delta_index < len(deltas):
                event = deltas[delta_index]
                yield f"data: {event.model_dump_json()}\n\n"
                delta_index += 1
            if current.status in {"completed", "failed"}:
                yield f"event: done\ndata: {current.status}\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/problems")
def list_problems_api() -> list[dict[str, Any]]:
    return [p.model_dump(mode="json") for p in _default_problems().list_problems()]


@app.post("/api/problems")
def register_problem(payload: ProblemRequest) -> dict[str, Any]:
    try:
        problem = _default_problems().register(
            payload.text,
            title=payload.title,
            source=payload.source,
            source_run_id=payload.source_run_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return problem.model_dump(mode="json")


@app.delete("/api/problems/{problem_id}")
def delete_problem(problem_id: str) -> Response:
    try:
        _default_problems().delete(problem_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@app.get("/api/approved")
def list_approved() -> list[dict[str, Any]]:
    return [p.model_dump(mode="json") for p in _default_problems().approved()]

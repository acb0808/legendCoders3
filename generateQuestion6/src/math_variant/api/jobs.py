"""생성 작업(Job) 저장소와 상태 전이 (T08).

Job 은 JSON 파일(data/jobs/<job_id>.json)로 영속화되어 서버 재시작에도 상태가 유지된다.
상태 전이: queued → running → completed | failed
"""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from math_variant.events import PipelineEvent


class CreateOptions(BaseModel):
    """생성 옵션 (웹 폼 → 파이프라인)."""

    model_config = ConfigDict(extra="forbid")

    difficulty_target: str = ""
    ideator_count: int = Field(default=3, ge=1, le=5)
    max_refine: int = Field(default=2, ge=0, le=3)


class GenerationJob(BaseModel):
    """생성 작업 하나."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    run_id: str
    source: dict[str, Any]
    options: CreateOptions = Field(default_factory=CreateOptions)
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    events: list[PipelineEvent] = Field(default_factory=list)
    error: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class JobStore:
    """data/jobs/*.json 형식의 작업 저장소. 스레드 안전."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, job_id: str) -> Path:
        return self.base_dir / f"{job_id}.json"

    def create(
        self,
        source_text: str,
        options: CreateOptions | None = None,
        source_mode: Literal["text", "problem"] = "text",
        source_label: str = "",
    ) -> GenerationJob:
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        job = GenerationJob(
            job_id=run_id,
            run_id=run_id,
            source={"mode": source_mode, "text": source_text, "label": source_label},
            options=options if options is not None else CreateOptions(),
        )
        self.save(job)
        return job

    def save(self, job: GenerationJob) -> None:
        with self._lock:
            job.updated_at = datetime.now(UTC)
            self._path(job.job_id).write_text(
                json.dumps(job.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def load(self, job_id: str) -> GenerationJob:
        path = self._path(job_id)
        with self._lock:
            if not path.is_file():
                raise ValueError(f"작업 없음: {job_id}")
            data = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        return GenerationJob.model_validate(data)

    def list_jobs(self) -> list[GenerationJob]:
        jobs: list[GenerationJob] = []
        with self._lock:
            for path in self.base_dir.glob("*.json"):
                jobs.append(
                    GenerationJob.model_validate(json.loads(path.read_text(encoding="utf-8")))
                )
        jobs.sort(key=lambda j: j.created_at.isoformat(), reverse=True)
        return jobs

    def _mutate(self, job_id: str, mutate: Callable[[GenerationJob], None]) -> GenerationJob:
        path = self._path(job_id)
        with self._lock:
            if not path.is_file():
                raise ValueError(f"작업 없음: {job_id}")
            data = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
            job = GenerationJob.model_validate(data)
            mutate(job)
            job.updated_at = datetime.now(UTC)
            path.write_text(
                json.dumps(job.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return job

    def append_event(self, job_id: str, event: PipelineEvent) -> None:
        self._mutate(job_id, lambda job: job.events.append(event))

    def set_status(
        self, job_id: str, status: Literal["queued", "running", "completed", "failed"]
    ) -> None:
        self._mutate(job_id, lambda job: setattr(job, "status", status))

    def complete(self, job_id: str, report: dict[str, Any]) -> None:
        def mutate(job: GenerationJob) -> None:
            job.status = "completed"
            job.report = report

        self._mutate(job_id, mutate)

    def fail(self, job_id: str, message: str, code: str = "JOB_FAILED") -> None:
        def mutate(job: GenerationJob) -> None:
            job.status = "failed"
            job.error = {"message": message, "code": code}

        self._mutate(job_id, mutate)

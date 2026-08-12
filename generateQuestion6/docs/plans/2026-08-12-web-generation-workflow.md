# 웹 생성 워크플로 구현 계획 — 문제 기반 새 문제 제작

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 웹에서 사용자가 원문제(텍스트 붙여넣기 또는 문제 라이브러리에서 선택)를 지정하고, 실제 LLM 다중 에이전트 파이프라인을 비동기 작업으로 실행하며, 단계 진행과 LLM 호출 로그를 SSE로 실시간 표시하고, 완료 후 기존 검토 화면으로 이어지며, 승인된 문제가 문제 라이브러리에 자동 보관되어 재사용되는 생성 워크플로를 구현한다.

**Architecture:** 기존 FastAPI 앱(`src/math_variant/api/app.py`)을 확장한다. `StructuredOutputEngine`과 `AgentPipeline`에 선택적 `on_event` 콜백을 추가해 이벤트를 방출하고, 백그라운드 스레드가 CLI와 동일한 파이프라인 배선(공급자·샌드박스)으로 `AgentPipeline.run()`을 실행한다. 진행 이벤트는 `JobStore`(JSON 영속화)에 기록되고 SSE(`text/event-stream`)로 스트리밍된다. 완료 시 `PipelineReport`를 `RunStore` 형식으로 변환(어댑터)해 기존 검토 화면이 그대로 동작하게 한다. Next.js는 `/create`(생성 폼), `/runs/{runId}/progress`(실시간 진행), `/problems`(라이브러리) 화면을 추가한다.

**Tech Stack:** Python 3.12, FastAPI + StreamingResponse(SSE), threading, pydantic v2(`extra="forbid"`), ruff/mypy-strict/pytest(백엔드 게이트). Next.js 16.3(App Router, `params`는 Promise), React 19, Vitest(프론트 게이트).

**설계 문서:** `docs/plans/2026-08-12-web-generation-workflow-design.md` (승인 완료)

**핵심 이벤트 구조:**
- `PipelineEvent.type = "stage" | "llm_call"`
- stage 이벤트: `{stage, status(started|done|failed), message, candidate_id?}`
- llm_call 이벤트: `{role, schema, provider, model, temperature, attempts, latency_ms, cost_usd, status(ok|error), summary, error?}`
- `StructuredOutputEngine.generate_structured()` 1회당 llm_call 1건, 파이프라인은 단계 이벤트 방출
- 기본값 `on_event=None` → 기존 CLI·테스트 무영향 (하위 호환)

**의존성 방향:** `providers/structured.py`와 `agents/pipeline.py`가 공통 이벤트 모델을 import한다. providers→api 의존은 금지하므로 이벤트 모델은 최상위 `src/math_variant/events.py`에 둔다 (설계 문서의 `api/events.py` 위치와 다르지만 의존성 순환이 없고 레이어가 깨끗하다).

---

## Task 1: 진행 이벤트 모델 + 요약기

**Files:**
- Create: `src/math_variant/events.py`
- Create: `tests/unit/events/test_events.py`

**Step 1: 실패 테스트 작성**

`tests/unit/events/test_events.py`:
```python
"""웹 생성 워크플로 — 진행 이벤트 모델·요약 테스트."""

from __future__ import annotations

from datetime import UTC, datetime

from math_variant.events import (
    EventStage,
    PipelineEvent,
    ROLE_TO_STAGE,
    summarize_response,
)


def test_stage_event_roundtrip() -> None:
    event = PipelineEvent(
        event_id="evt-1",
        type="stage",
        stage=EventStage.PLANNER,
        status="started",
        message="기획 시작",
        ts=datetime.now(UTC),
    )
    dumped = event.model_dump(mode="json")
    assert dumped["stage"] == "planner"
    assert dumped["type"] == "stage"
    restored = PipelineEvent.model_validate(dumped)
    assert restored.message == "기획 시작"


def test_llm_call_event_roundtrip() -> None:
    event = PipelineEvent(
        event_id="evt-2",
        type="llm_call",
        stage=EventStage.IDEATION,
        status="done",
        message="",
        ts=datetime.now(UTC),
        data={
            "role": "ideator",
            "schema": "IdeationOutput",
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "temperature": 1.4,
            "attempts": 1,
            "latency_ms": 4231,
            "cost_usd": 0.0021,
            "ok": True,
            "summary": {"idea_id": "idea-0", "title": "질문 역전"},
        },
    )
    assert event.model_dump(mode="json")["data"]["provider"] == "deepseek"


def test_role_to_stage_mapping() -> None:
    assert ROLE_TO_STAGE["planner"] == EventStage.PLANNER
    assert ROLE_TO_STAGE["ideator"] == EventStage.IDEATION
    assert ROLE_TO_STAGE["generator"] == EventStage.GENERATION
    assert ROLE_TO_STAGE["blind_solver"] == EventStage.BLIND
    assert ROLE_TO_STAGE["vision"] == EventStage.GENERATION


def test_summarize_known_schemas() -> None:
    assert summarize_response("IdeationOutput", {"idea_id": "i1", "title": "질문 역전"}) == {
        "idea_id": "i1",
        "title": "질문 역전",
    }
    assert summarize_response("GeneratorOutput", {"final_answer_claim": "8sqrt(2)"}) == {
        "final_answer_claim": "8sqrt(2)"
    }
    assert summarize_response("CodeReviewOutput", {"verdict": "APPROVE", "safe": True}) == {
        "verdict": "APPROVE"
    }


def test_summarize_unknown_schema_returns_scalar_keys() -> None:
    assert summarize_response("UnknownSchema", {"x": 1, "problem_text": "본문"}) == {
        "problem_text": "본문"
    }
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/events/test_events.py -v`
Expected: FAIL — `math_variant.events` 모듈 없음.

**Step 3: 구현**

`src/math_variant/events.py`:
```python
"""진행·LLM 호출 이벤트 모델 (웹 생성 워크플로).

의존성 방향: providers/structured.py 와 agents/pipeline.py 가 공통으로 import 한다.
providers → api 로의 의존을 피하기 위해 최상위 모듈에 둔다. (설계 문서의 api/events.py
위치와 다르지만 레이어를 깨끗하게 유지한다.)
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EventStage(StrEnum):
    """파이프라인 진행 단계."""

    PLANNER = "planner"
    IDEATION = "ideation"
    SELECTION = "selection"
    GENERATION = "generation"
    CODE_REVIEW = "code_review"
    SANDBOX = "sandbox"
    BLIND = "blind"
    CRITIC = "critic"
    JUDGE = "judge"
    DONE = "done"


ROLE_TO_STAGE: dict[str, EventStage] = {
    "source_analyzer": EventStage.PLANNER,
    "planner": EventStage.PLANNER,
    "ideator": EventStage.IDEATION,
    "selector": EventStage.SELECTION,
    "generator": EventStage.GENERATION,
    "vision": EventStage.GENERATION,
    "code_reviewer": EventStage.CODE_REVIEW,
    "critic": EventStage.CRITIC,
    "judge": EventStage.JUDGE,
    "blind_solver": EventStage.BLIND,
}


_SCHEMA_SUMMARIES: dict[str, tuple[str, ...]] = {
    "PlannerOutput": ("core_concepts", "domain", "objective"),
    "IdeationOutput": ("idea_id", "title", "changed_dimensions"),
    "SelectionOutput": ("adopted_ideas",),
    "GeneratorOutput": ("final_answer_claim",),
    "CodeReviewOutput": ("verdict", "safe", "test_consistent"),
    "CriticOutput": ("score", "recommendation"),
    "JudgeOutput": ("ranking",),
    "VisionOutput": ("caption",),
    "BlindSolution": ("status", "answer_set"),
}


def summarize_response(schema: str, data: dict[str, Any]) -> dict[str, Any]:
    """구조화 응답에서 핵심 필드만 짧게 추출한다 (호출 로그용)."""
    keys = _SCHEMA_SUMMARIES.get(schema, ())
    if not keys:
        keys = tuple(k for k in ("candidate_id", "problem_text", "final_answer_claim") if k in data)
    return {k: data[k] for k in keys if k in data}


class PipelineEvent(BaseModel):
    """진행(단계) 또는 LLM 호출 이벤트."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    type: Literal["stage", "llm_call"]
    stage: EventStage
    status: Literal["started", "done", "failed"] = "done"
    message: str = ""
    candidate_id: str | None = None
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data: dict[str, Any] = Field(default_factory=dict)
```

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/events/test_events.py -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/math_variant/events.py tests/unit/events/test_events.py
git commit -m "feat: add pipeline event model and response summarizer"
```

---

## Task 2: StructuredOutputEngine LLM 호출 이벤트

**Files:**
- Modify: `src/math_variant/providers/structured.py:32-49` (생성자)
- Modify: `src/math_variant/providers/structured.py:51-179` (generate_structured)
- Create: `tests/unit/providers/test_structured_events.py`

**Step 1: 실패 테스트 작성**

`tests/unit/providers/test_structured_events.py`:
```python
"""T08 — 엔진이 LLM 호출 이벤트를 방출하는지 테스트."""

from __future__ import annotations

from math_variant.events import EventStage, PipelineEvent
from math_variant.providers.contracts import ProviderResponse, RolePolicy, StructuredRequest
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine


class _Provider:
    name = "fake"

    def complete(self, prompt, policy):
        return type(
            "Completion",
            (),
            {"provider": "fake", "raw_text": '{"title": "질문 역전"}', "latency_ms": 10, "cost_usd": 0.0},
        )()


def test_engine_emits_llm_call_event() -> None:
    from math_variant.agents.schemas import IdeationOutput, register_agent_schemas

    schemas = SchemaRegistry()
    register_agent_schemas(schemas)
    emitted: list[PipelineEvent] = []
    engine = StructuredOutputEngine(
        primary=None, fallback=None, schemas=schemas, on_event=emitted.append
    )
    engine.role_resolver = _FakeResolver()

    response = engine.generate_structured(
        StructuredRequest(
            request_id="ideator-0",
            role=RolePolicy.IDEATOR,
            prompt="p",
            response_schema="IdeationOutput",
        ),
        policy=None,
    )
    assert response.ok
    assert len(emitted) == 1
    event = emitted[0]
    assert event.type == "llm_call"
    assert event.stage == EventStage.IDEATION
    assert event.data["provider"] == "fake"
    assert event.data["schema"] == "IdeationOutput"
    assert event.data["ok"] is True
    assert event.data["summary"] == {"title": "질문 역전"}


def test_engine_without_on_event_still_works() -> None:
    from math_variant.agents.schemas import register_agent_schemas

    schemas = SchemaRegistry()
    register_agent_schemas(schemas)
    engine = StructuredOutputEngine(primary=None, fallback=None, schemas=schemas)
    engine.role_resolver = _FakeResolver()
    response = engine.generate_structured(
        StructuredRequest(
            request_id="r",
            role=RolePolicy.IDEATOR,
            prompt="p",
            response_schema="IdeationOutput",
        ),
        policy=None,
    )
    assert response.ok


class _FakeResolver:
    def provider_for(self, role: RolePolicy):
        return _Provider()

    def fallback_for(self, role: RolePolicy):
        return None

    def policy_for(self, role: RolePolicy):
        return type("Policy", (), {"provider": "fake", "model": "fake-model", "temperature": 0.2, "max_tokens": 100})()
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/providers/test_structured_events.py -v`
Expected: FAIL — `on_event` 키워드 인자 없음.

**Step 3: 구현**

`src/math_variant/providers/structured.py` — 생성자에 `on_event` 추가:
```python
    def __init__(
        self,
        primary: LLMProvider | None,
        fallback: LLMProvider | None,
        schemas: SchemaRegistry,
        max_repair_attempts: int = 1,
        logger: logging.Logger | None = None,
        role_resolver: RoleResolver | None = None,
        on_event: Callable[[PipelineEvent], None] | None = None,
    ) -> None:
        ...
        self.on_event = on_event
```

import 추가:
```python
from typing import Any, Callable
from math_variant.events import EventStage, PipelineEvent, ROLE_TO_STAGE, summarize_response
```

`generate_structured` 마지막에, 반환 전에 이벤트를 방출하는 헬퍼를 추가하고 두 반환 경로(성공/실패)에 연결한다:

성공 경로 (data 반환 직전):
```python
                    self._emit_llm_call(
                        request, resolved_policy, ok=True, data=data,
                        final_provider=final_provider, attempts=attempts,
                        latency=latency, cost=cost, error=None,
                    )
                    return ProviderResponse(...)
```

실패 경로 (반환 직전):
```python
        self._emit_llm_call(
            request, resolved_policy, ok=False, data=None,
            final_provider=final_provider, attempts=attempts,
            latency=latency, cost=cost, error=last_error,
        )
        return ProviderResponse(...)
```

헬퍼 메서드:
```python
    def _emit_llm_call(
        self,
        request: StructuredRequest,
        policy: ModelPolicy,
        *,
        ok: bool,
        data: dict[str, Any] | None,
        final_provider: str | None,
        attempts: int,
        latency: int,
        cost: float,
        error: ProviderError | None,
    ) -> None:
        if self.on_event is None:
            return
        event = PipelineEvent(
            event_id=f"{request.request_id}-{attempts}",
            type="llm_call",
            stage=ROLE_TO_STAGE.get(request.role.value, EventStage.DONE),
            status="done" if ok else "failed",
            ts=datetime.now(UTC),
            data={
                "role": request.role.value,
                "schema": request.response_schema,
                "provider": final_provider or policy.provider,
                "model": policy.model,
                "temperature": policy.temperature,
                "attempts": attempts,
                "latency_ms": latency,
                "cost_usd": cost,
                "ok": ok,
                "summary": summarize_response(request.response_schema, data or {}),
                "error": error.model_dump() if error else None,
            },
        )
        self.on_event(event)
```

datetime·UTC import 추가: `from datetime import UTC, datetime`.

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/providers/test_structured_events.py -v`
Expected: PASS

**Step 5: 회귀 확인**

Run: `.venv\Scripts\python -m pytest tests/contract/providers/test_structured_output.py -v`
Expected: PASS (기존 계약 유지)

**Step 6: 커밋**

```bash
git add src/math_variant/providers/structured.py tests/unit/providers/test_structured_events.py
git commit -m "feat: emit llm_call events from structured engine (optional)"
```

---

## Task 3: 파이프라인 단계 이벤트 + 난이도 옵션

**Files:**
- Modify: `src/math_variant/agents/pipeline.py:96-130` (생성자)
- Modify: `src/math_variant/agents/pipeline.py:132-194` (run)
- Modify: `src/math_variant/agents/planner.py:21-29` (plan에 난이도 옵션)
- Modify: `tests/unit/agents/test_pipeline.py` (난이도 전달 테스트 추가)
- Create: `tests/unit/agents/test_pipeline_events.py`

**Step 1: 실패 테스트 작성**

`tests/unit/agents/test_pipeline_events.py`:
```python
"""T08 — 파이프라인이 단계 이벤트를 방출하는지 테스트."""

from __future__ import annotations

from pathlib import Path

from math_variant.agents.code_reviewer import CodeReviewAgent
from math_variant.agents.critic import CriticAgent
from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.ideator import IdeatorAgent
from math_variant.agents.judge import JudgeAgent
from math_variant.agents.pipeline import AgentPipeline
from math_variant.agents.planner import PlannerAgent
from math_variant.agents.selector import SelectorAgent
from math_variant.events import EventStage, PipelineEvent
from math_variant.providers.contracts import ProviderResponse, RolePolicy
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine
from math_variant.sandbox.contracts import SandboxResult, SandboxStatus
from math_variant.services.blind_solver import BlindConsensus

_PLANNER = {
    "core_concepts": ["포물선", "평행이동"],
    "auxiliary_concepts": [],
    "objective": "상수의 값을 구하시오",
    "answer_type": "expression",
    "domain": "도형의 방정식",
    "preservation_goals": ["평행이동 성질"],
    "strategy": {
        "difficulty_target": "중상",
        "preservation_goals": ["평행이동"],
        "variation_direction": ["질문 역전"],
        "quality_criteria": ["유일해"],
    },
    "unresolved_assumptions": [],
}
_IDEA = {
    "idea_id": "idea-1",
    "title": "질문 역전",
    "preserved_concepts": ["평행이동"],
    "changed_dimensions": ["objective", "condition_topology", "solution_route", "data_domain"],
    "change_description": ["역전"],
    "construction_blueprint": "a를 구하게 한다",
}
_CANDIDATE = {
    "problem_text": "문제 본문",
    "formalization": {"symbols": ["x"], "constraints": [], "goal": "a의 값"},
    "final_answer_claim": "8sqrt(2)",
    "solution_steps": [{"step_id": "s1", "statement": "단계"}],
    "transformation_evidence": [{"dimension": "objective", "description": "역전"}],
    "verification_script": "result = {'verdict': 'PASS'}",
}
_REVIEW = {"verdict": "APPROVE", "safe": True, "test_consistent": True, "feedback": ""}
_CRITIC = {
    "score": 8.0,
    "difficulty_estimate": "중상",
    "criteria_scores": {},
    "comments": [],
    "recommendation": "PASS",
}
_JUDGE = {"ranking": [{"candidate_id": "cand-1", "score": 8.0, "reason": "통과"}], "summary": ""}


class _Engine(StructuredOutputEngine):
    def __init__(self, responses: dict[str, list[dict]]) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self.responses = {k: list(v) for k, v in responses.items()}
        self.calls: list[tuple[RolePolicy, str]] = []

    def generate_structured(self, request, policy=None) -> ProviderResponse:
        self.calls.append((request.role, request.prompt))
        queue = self.responses.get(request.role.value, [])
        if not queue:
            return ProviderResponse(request_id=request.request_id, ok=False)
        data = queue.pop(0)
        return ProviderResponse(request_id=request.request_id, ok=True, data=data)


class _PassSandbox:
    name = "fake"

    def execute(self, request) -> SandboxResult:
        return SandboxResult(
            result_id="r",
            request_id=request.request_id,
            status=SandboxStatus.COMPLETED,
            output_json={"result": {"verdict": "PASS"}},
        )


class _PassSolvers:
    def solve_both(self, problem_text: str) -> BlindConsensus:
        return BlindConsensus(status="PASS", solver_a="A", solver_b="B", reason="동치")


def _build_pipeline(engine: _Engine, tmp_path: Path, on_event) -> AgentPipeline:
    return AgentPipeline(
        planner=PlannerAgent(engine, "p"),
        ideator=IdeatorAgent(engine, "p"),
        selector=SelectorAgent(engine, "p"),
        generator=GeneratorAgent(engine, "p"),
        code_reviewer=CodeReviewAgent(engine, "p"),
        critic=CriticAgent(engine, "p"),
        judge=JudgeAgent(engine, "p"),
        vision=None,
        sandbox=_PassSandbox(),  # type: ignore[arg-type]
        blind_solvers=_PassSolvers(),  # type: ignore[arg-type]
        runs_dir=tmp_path,
        max_workers=4,
        max_refine=1,
        ideator_count=1,
        on_event=on_event,
    )


def test_pipeline_emits_stage_events_in_order(tmp_path) -> None:
    engine = _Engine(
        {
            "planner": [_PLANNER],
            "ideator": [_IDEA],
            "selector": [{"adopted_ideas": ["idea-1"], "rationale": "부합"}],
            "generator": [_CANDIDATE],
            "code_reviewer": [_REVIEW],
            "critic": [_CRITIC],
            "judge": [_JUDGE],
        }
    )
    events: list[PipelineEvent] = []
    _build_pipeline(engine, tmp_path, events.append).run("원문")

    stages = [e.stage for e in events]
    assert EventStage.PLANNER in stages
    assert EventStage.IDEATION in stages
    assert EventStage.SELECTION in stages
    assert EventStage.GENERATION in stages
    assert EventStage.CODE_REVIEW in stages
    assert EventStage.SANDBOX in stages
    assert EventStage.BLIND in stages
    assert EventStage.CRITIC in stages
    assert EventStage.JUDGE in stages
    assert EventStage.DONE in stages
    # 마지막은 done(완료)
    assert events[-1].stage == EventStage.DONE
    assert events[-1].status == "done"


def test_pipeline_emits_sandbox_and_candidate_scoped_events(tmp_path) -> None:
    engine = _Engine(
        {
            "planner": [_PLANNER],
            "ideator": [_IDEA],
            "selector": [{"adopted_ideas": ["idea-1"], "rationale": "부합"}],
            "generator": [_CANDIDATE],
            "code_reviewer": [_REVIEW],
            "critic": [_CRITIC],
            "judge": [_JUDGE],
        }
    )
    events: list[PipelineEvent] = []
    _build_pipeline(engine, tmp_path, events.append).run("원문")

    sandbox_events = [e for e in events if e.stage == EventStage.SANDBOX]
    assert sandbox_events
    assert sandbox_events[0].status == "started"
    assert sandbox_events[1].status == "done"
    assert sandbox_events[0].candidate_id == "cand-1"
```

`tests/unit/agents/test_pipeline.py`에 추가 (난이도 옵션이 planner 프롬프트에 전달되는지):
```python
def test_pipeline_forwards_difficulty_target_to_planner(tmp_path) -> None:
    engine = _build_engine()
    _pipeline(engine, tmp_path).run("원문", difficulty_target="상")
    planner_prompt = next(p for role, p in engine.calls if role == RolePolicy.PLANNER)
    assert "난이도 목표" in planner_prompt
    assert "상" in planner_prompt
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/agents/test_pipeline_events.py tests/unit/agents/test_pipeline.py -v`
Expected: FAIL — `on_event`·`difficulty_target` 인자 없음.

**Step 3: 구현**

`src/math_variant/agents/planner.py` — `plan`에 난이도 옵션 추가:
```python
    def plan(self, source_text: str, difficulty_target: str = "") -> PlannerOutput:
        prompt = f"{self.prompt_bundle}\n\n[원문]\n{source_text}"
        if difficulty_target.strip():
            prompt += f"\n[난이도 목표]\n{difficulty_target}"
        data = request_structured(...)
        return PlannerOutput.model_validate(data)
```

`src/math_variant/agents/pipeline.py`:
- import: `from math_variant.events import EventStage, PipelineEvent`
- import: `from collections.abc import Callable`
- 생성자에 `on_event: Callable[[PipelineEvent], None] | None = None` 추가, `self.on_event` 저장
- `_emit` 헬퍼 추가:
```python
    def _emit(
        self,
        stage: EventStage,
        status: str,
        message: str = "",
        candidate_id: str | None = None,
    ) -> None:
        if self.on_event is None:
            return
        self.on_event(
            PipelineEvent(
                event_id=f"{stage.value}-{status}-{self._event_seq}",
                type="stage",
                stage=stage,
                status=status,  # type: ignore[arg-type]
                message=message,
                candidate_id=candidate_id,
            )
        )
        self._event_seq += 1
```
  생성자에서 `self._event_seq = 0` 초기화.

- `run` 시그니처: `def run(self, source_text: str, strategy_brief: str = "", difficulty_target: str = "") -> PipelineReport:`
- `run` 내부에서 단계 이벤트 방출:
  - 기획 시작/완료:
    ```python
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        self._emit(EventStage.PLANNER, "started", "원문을 분석하여 변형 전략을 수립한다")
        planner_out = self.planner.plan(source_text, difficulty_target=difficulty_target)
        self._emit(EventStage.PLANNER, "done", "변형 스펙·전략 수립 완료")
    ```
  - 발상:
    ```python
        self._emit(EventStage.IDEATION, "started", f"변형 아이디어 {self.ideator_count}개 발상")
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            ideas = list(pool.map(...))
        self._emit(EventStage.IDEATION, "done", f"발상 완료 ({len(ideas)}개)")
    ```
  - 선별:
    ```python
        self._emit(EventStage.SELECTION, "started", "아이디어 채택 선별")
        selection = self.selector.select(ideas, strategy_brief)
        self._emit(EventStage.SELECTION, "done", f"채택 {len(adopted)}개")
    ```
  - `_grow_candidate` 내부 후보별 단계 이벤트 (candidate_id 스코프):
    - 생성: `self._emit(EventStage.GENERATION, "started", "문제 생성", candidate_id)` / done
    - 코드심사: `CODE_REVIEW` started/done
    - 샌드박스: `SANDBOX` started/done (review.approves일 때만)
    - 블라인드: `BLIND` started/done
    - 비평: `CRITIC` started/done
    - 상태 메시지에 검증 결과 포함 (예: `f"샌드박스 검증: {test_outcome.verdict.value}"`)
  - 집계:
    ```python
        self._emit(EventStage.JUDGE, "started", "최종 랭킹 집계")
        judge_out = self.judge.judge(rank_entries, run_id=run_id)
        self._emit(EventStage.JUDGE, "done", "집계 완료")
    ```
  - 완료 (report 반환 직전):
    ```python
        self._emit(EventStage.DONE, "done", f"완료 — 후보 {len(report.candidates)}건")
    ```
  - `adopted`가 비어있는 early return 직전에도 `self._emit(EventStage.DONE, "failed", "채택된 아이디어가 없다")` 방출.

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/agents/test_pipeline_events.py tests/unit/agents/test_pipeline.py -v`
Expected: PASS

**Step 5: 회귀 확인**

Run: `.venv\Scripts\python -m ruff check src tests infra; .venv\Scripts\python -m mypy`
Expected: 통과. (mypy에서 `status` Literal 타입 협의가 필요하면 `Literal["started","done","failed"]`로 명시하거나 주석 `# type: ignore` 대신 타입 어노테이션 사용. `_emit`의 `status: Literal[...]` 파라미터로 선언.)

**Step 6: 커밋**

```bash
git add src/math_variant/agents/pipeline.py src/math_variant/agents/planner.py tests/unit/agents/test_pipeline.py tests/unit/agents/test_pipeline_events.py
git commit -m "feat: emit stage events from pipeline and accept difficulty option"
```

---

## Task 4: 파이프라인 팩토리 (CLI·웹 공용)

**Files:**
- Create: `src/math_variant/pipeline_factory.py`
- Modify: `src/math_variant/cli.py:260-358` (run_pipeline가 팩토리 사용)
- Create: `tests/unit/test_pipeline_factory.py`

**Step 1: 실패 테스트 작성**

`tests/unit/test_pipeline_factory.py`:
```python
"""T08 — 파이프라인 팩토리 테스트."""

from __future__ import annotations

from pathlib import Path

from math_variant.agents.pipeline import AgentPipeline
from math_variant.pipeline_factory import build_agent_pipeline


def test_build_agent_pipeline_returns_configured_pipeline(tmp_path: Path) -> None:
    pipeline = build_agent_pipeline(
        source_text="원문 본문",
        difficulty_target="중상",
        ideator_count=2,
        max_refine=1,
        on_event=None,
        runs_dir=tmp_path,
        figures_dir=tmp_path / "figures",
        sandbox_image="math-variant-sandbox:test",
    )
    assert isinstance(pipeline, AgentPipeline)
    assert pipeline.ideator_count == 2
    assert pipeline.max_refine == 1


def test_build_agent_pipeline_forwards_difficulty() -> None:
    # on_event None 이어도 난이도 옵션이 팩토리에 전달되어 파이프라인이 구성된다.
    pipeline = build_agent_pipeline(
        source_text="x",
        difficulty_target="상",
        ideator_count=1,
        max_refine=0,
        on_event=None,
        runs_dir=Path("runs"),
        figures_dir=Path("runs/figures"),
    )
    assert isinstance(pipeline, AgentPipeline)
```

> 참고: 팩토리는 `ProviderSettings()`(`.env`)를 읽어 공급자 레지스트리를 만든다. 테스트 환경에 API 키가 있어야 하므로, 팩토리는 **엔진 생성만** 하고 실제 provider 완성은 지연 호출하는 구조로 설계한다. 즉 `build_agent_pipeline`은 `StructuredOutputEngine`과 에이전트를 구성만 하고 LLM 호출은 파이프라인 실행 시점에 발생한다. `.env`에 키가 없어도 생성은 성공해야 한다 (키는 호출 시점에 필요). 구현은 `build_provider_registry(settings)`를 호출하는데, 각 어댑터가 키를 지연 읽기한다면 안전하다. 이 테스트가 실패하면 어댑터의 키 지연 읽기 여부를 확인한다.

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/test_pipeline_factory.py -v`
Expected: FAIL — 모듈 없음.

**Step 3: 구현**

`src/math_variant/pipeline_factory.py`:
```python
"""파이프라인 팩토리 — CLI·웹(API)이 공용으로 사용하는 AgentPipeline 구성.

실제 LLM 공급자 호출은 여기서 하지 않고 AgentPipeline.run() 시점에 발생한다.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from math_variant.agents.blind import LLMBlindSolver
from math_variant.agents.code_reviewer import CodeReviewAgent
from math_variant.agents.critic import CriticAgent
from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.ideator import IdeatorAgent
from math_variant.agents.judge import JudgeAgent
from math_variant.agents.pipeline import AgentPipeline
from math_variant.agents.planner import PlannerAgent
from math_variant.agents.schemas import register_agent_schemas
from math_variant.agents.selector import SelectorAgent
from math_variant.agents.vision_artist import VisionArtist
from math_variant.events import PipelineEvent
from math_variant.providers.factory import build_provider_registry
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.resolver import RoleResolver
from math_variant.providers.settings import ProviderSettings
from math_variant.providers.structured import StructuredOutputEngine
from math_variant.sandbox.provider import DockerSandboxProvider
from math_variant.services.blind_solver import BlindSolver

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def build_agent_pipeline(
    *,
    source_text: str,
    difficulty_target: str = "",
    ideator_count: int = 3,
    max_refine: int = 2,
    on_event: Callable[[PipelineEvent], None] | None = None,
    runs_dir: Path,
    figures_dir: Path,
    sandbox_image: str = "math-variant-sandbox:test",
    forbidden_context: dict[str, str] | None = None,
) -> AgentPipeline:
    """설정·공급자·에이전트를 묶어 AgentPipeline 을 구성한다."""
    settings = ProviderSettings()
    registry = build_provider_registry(settings)
    schemas = SchemaRegistry()
    register_agent_schemas(schemas)
    resolver = RoleResolver(settings.role_policy(), registry)
    engine = StructuredOutputEngine(primary=None, fallback=None, schemas=schemas, on_event=on_event)
    engine.role_resolver = resolver

    def _prompt(name: str) -> str:
        return (PROMPTS_DIR / name).read_text(encoding="utf-8")

    return AgentPipeline(
        planner=PlannerAgent(engine, _prompt("planner.md")),
        ideator=IdeatorAgent(engine, _prompt("ideator.md")),
        selector=SelectorAgent(engine, _prompt("selector.md")),
        generator=GeneratorAgent(engine, _prompt("candidate_generator.md")),
        code_reviewer=CodeReviewAgent(engine, _prompt("code_reviewer.md")),
        critic=CriticAgent(engine, _prompt("critic.md")),
        judge=JudgeAgent(engine, _prompt("judge.md")),
        vision=VisionArtist(engine, _prompt("vision.md"), figures_dir),
        sandbox=DockerSandboxProvider(image=sandbox_image),
        blind_solvers=BlindSolver(
            LLMBlindSolver(engine, _prompt("blind_solver.md"), "A"),
            LLMBlindSolver(engine, _prompt("blind_solver.md"), "B"),
            forbidden_context or {},
        ),
        runs_dir=runs_dir,
        ideator_count=ideator_count,
        max_refine=max_refine,
        on_event=on_event,
    )
```

`src/math_variant/cli.py` — `run_pipeline`의 배선 부분을 팩토리로 교체:
```python
    from math_variant.pipeline_factory import build_agent_pipeline
    ...
    pipeline = build_agent_pipeline(
        source_text=question["question_text"],
        difficulty_target="",
        ideator_count=3,
        max_refine=2,
        on_event=None,
        runs_dir=Path("runs"),
        figures_dir=Path("runs") / "figures",
        sandbox_image="math-variant-sandbox:test",
        forbidden_context={"원문 정답": str(question.get("answer") or ""), "해설": ""},
    )
```
(이제 cli의 로컬 import에서 에이전트·공급자·샌드박스·blind 관련 import를 제거한다. `normalize_source` 호출은 그대로.)

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/test_pipeline_factory.py -v`
Expected: PASS

**Step 5: CLI 회귀 확인 (도움말/인자 파싱)**

Run: `.venv\Scripts\python -m math_variant.cli run --help` (또는 `python -c "import math_variant.cli; math_variant.cli.parse_run_args([])"`)
Expected: 파싱 오류 없음. (실제 LLM 실행은 유료라 실행하지 않는다.)

Run: `.venv\Scripts\python -m pytest -q` (전체 회귀)
Expected: PASS (154+ 통과)

**Step 6: 커밋**

```bash
git add src/math_variant/pipeline_factory.py src/math_variant/cli.py tests/unit/test_pipeline_factory.py
git commit -m "refactor: extract shared agent pipeline factory for cli and web"
```

---

## Task 5: 문제 라이브러리 저장소 (ProblemStore)

**Files:**
- Create: `src/math_variant/api/problems.py`
- Create: `tests/unit/api/test_problems.py`

**Step 1: 실패 테스트 작성**

`tests/unit/api/test_problems.py`:
```python
"""T08 — 문제 라이브러리 저장소 테스트."""

from __future__ import annotations

from pathlib import Path

from math_variant.api.problems import ProblemStore
from math_variant.services.normalize import normalize_source


def _store(tmp_path: Path) -> ProblemStore:
    return ProblemStore(tmp_path)


def test_register_and_list(tmp_path: Path) -> None:
    store = _store(tmp_path)
    problem = store.register("포물선 y=x^2 의 접선을 구하시오.", title="T1")
    assert problem.source == "manual"
    listed = store.list()
    assert len(listed) == 1
    assert listed[0].problem_id == problem.problem_id


def test_register_is_idempotent_by_normalized_hash(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.register("포물선 y = x^2 의 접선", title="A")
    second = store.register("포물선 y = x^2 의 접선", title="B")
    assert first.problem_id == second.problem_id
    assert len(store.list()) == 1


def test_delete_removes_problem(tmp_path: Path) -> None:
    store = _store(tmp_path)
    problem = store.register("본문")
    store.delete(problem.problem_id)
    assert store.list() == []


def test_approved_returns_only_approved(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.register("원문제")
    approved = store.register("승인된 문제", source="approved", source_run_id="run-1")
    assert [p.problem_id for p in store.approved()] == [approved.problem_id]


def test_register_approved_stores_run_ref(tmp_path: Path) -> None:
    store = _store(tmp_path)
    problem = store.register("본문", source="approved", source_run_id="run-abc")
    assert problem.source_run_id == "run-abc"
    assert problem.text_hash == __import__("hashlib").sha256(
        normalize_source("본문").encode("utf-8")
    ).hexdigest()


def test_problem_not_found_raises(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        store.delete("missing")
    except ValueError:
        pass
    else:
        raise AssertionError("존재하지 않는 문제 삭제는 실패해야 한다")
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/api/test_problems.py -v`
Expected: FAIL — 모듈 없음.

**Step 3: 구현**

`src/math_variant/api/problems.py`:
```python
"""문제 라이브러리 저장소 (T08).

- 직접 등록(source="manual")과 승인 문제 자동 등록(source="approved")을 모두 저장한다.
- 중복 방지: 정규화 텍스트의 sha256 해시로 판정해 멱등으로 동작한다.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from math_variant.services.normalize import normalize_source


class Problem(BaseModel):
    """라이브러리 문제 하나."""

    model_config = ConfigDict(extra="forbid")

    problem_id: str
    title: str = ""
    text: str = Field(min_length=1)
    source: Literal["manual", "approved"] = "manual"
    source_run_id: str | None = None
    text_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProblemStore:
    """data/problems/*.json 형식의 문제 라이브러리."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, problem_id: str) -> Path:
        return self.base_dir / f"{problem_id}.json"

    def list(self) -> list[Problem]:
        problems: list[Problem] = []
        for path in sorted(self.base_dir.glob("*.json")):
            problems.append(Problem.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        problems.sort(key=lambda p: p.created_at.isoformat(), reverse=True)
        return problems

    def approved(self) -> list[Problem]:
        return [p for p in self.list() if p.source == "approved"]

    def get(self, problem_id: str) -> Problem:
        path = self._path(problem_id)
        if not path.is_file():
            raise ValueError(f"문제 없음: {problem_id}")
        return Problem.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def register(
        self,
        text: str,
        title: str = "",
        source: Literal["manual", "approved"] = "manual",
        source_run_id: str | None = None,
    ) -> Problem:
        """문제를 등록한다. 정규화 텍스트 해시로 중복이면 기존 문제를 반환한다."""
        text_hash = hashlib.sha256(normalize_source(text).encode("utf-8")).hexdigest()
        existing = next((p for p in self.list() if p.text_hash == text_hash), None)
        if existing is not None:
            return existing
        problem = Problem(
            problem_id=f"problem-{uuid.uuid4().hex[:8]}",
            title=title,
            text=text,
            source=source,
            source_run_id=source_run_id,
            text_hash=text_hash,
        )
        self._path(problem.problem_id).write_text(
            json.dumps(problem.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return problem

    def delete(self, problem_id: str) -> None:
        path = self._path(problem_id)
        if not path.is_file():
            raise ValueError(f"문제 없음: {problem_id}")
        path.unlink()
```

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/api/test_problems.py -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/math_variant/api/problems.py tests/unit/api/test_problems.py
git commit -m "feat: add idempotent problem library store"
```

---

## Task 6: 생성 작업 저장소 (JobStore)

**Files:**
- Create: `src/math_variant/api/jobs.py`
- Create: `tests/unit/api/test_jobs.py`

**Step 1: 실패 테스트 작성**

`tests/unit/api/test_jobs.py`:
```python
"""T08 — 생성 작업(Job) 저장소 테스트."""

from __future__ import annotations

from pathlib import Path

from math_variant.api.jobs import CreateOptions, GenerationJob, JobStore
from math_variant.events import EventStage, PipelineEvent


def _store(tmp_path: Path) -> JobStore:
    return JobStore(tmp_path)


def _job(**overrides) -> GenerationJob:
    defaults = dict(
        job_id="job-1",
        run_id="run-1",
        source={"mode": "text", "text": "원문"},
        options=CreateOptions(),
        status="queued",
        events=[],
        error=None,
        report=None,
    )
    defaults.update(overrides)
    return GenerationJob(**defaults)


def test_create_save_load(tmp_path: Path) -> None:
    store = _store(tmp_path)
    job = store.create("원문", CreateOptions(difficulty_target="중상"))
    assert job.status == "queued"
    loaded = store.load(job.job_id)
    assert loaded.run_id == job.run_id
    assert loaded.options.difficulty_target == "중상"


def test_append_event_persists(tmp_path: Path) -> None:
    store = _store(tmp_path)
    job = store.create("원문", CreateOptions())
    event = PipelineEvent(
        event_id="e1",
        type="stage",
        stage=EventStage.PLANNER,
        status="started",
        message="기획 시작",
    )
    store.append_event(job.job_id, event)
    reloaded = store.load(job.job_id)
    assert len(reloaded.events) == 1
    assert reloaded.events[0].stage == EventStage.PLANNER


def test_set_status_and_error(tmp_path: Path) -> None:
    store = _store(tmp_path)
    job = store.create("원문", CreateOptions())
    store.set_status(job.job_id, "running")
    assert store.load(job.job_id).status == "running"
    store.fail(job.job_id, "boom", "AGENT_UNRESOLVED")
    failed = store.load(job.job_id)
    assert failed.status == "failed"
    assert failed.error == {"message": "boom", "code": "AGENT_UNRESOLVED"}


def test_list_sorted_by_created_desc(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create("첫번째")
    store.create("두번째")
    jobs = store.list()
    assert len(jobs) == 2
    assert jobs[0].job_id != jobs[1].job_id


def test_load_missing_raises(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        store.load("missing")
    except ValueError:
        pass
    else:
        raise AssertionError("존재하지 않는 job 조회는 실패해야 한다")
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/api/test_jobs.py -v`
Expected: FAIL — 모듈 없음.

**Step 3: 구현**

`src/math_variant/api/jobs.py`:
```python
"""생성 작업(Job) 저장소와 상태 전이 (T08).

Job 은 JSON 파일(data/jobs/<job_id>.json)로 영속화되어 서버 재시작에도 상태가 유지된다.
상태 전이: queued → running → completed | failed
"""

from __future__ import annotations

import json
import threading
import uuid
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
        options: CreateOptions,
        source_mode: Literal["text", "problem"] = "text",
        source_label: str = "",
    ) -> GenerationJob:
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        job = GenerationJob(
            job_id=run_id,
            run_id=run_id,
            source={"mode": source_mode, "text": source_text, "label": source_label},
            options=options,
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
        if not path.is_file():
            raise ValueError(f"작업 없음: {job_id}")
        with self._lock:
            data = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        return GenerationJob.model_validate(data)

    def list(self) -> list[GenerationJob]:
        jobs: list[GenerationJob] = []
        with self._lock:
            for path in self.base_dir.glob("*.json"):
                jobs.append(GenerationJob.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        jobs.sort(key=lambda j: j.created_at.isoformat(), reverse=True)
        return jobs

    def append_event(self, job_id: str, event: PipelineEvent) -> None:
        job = self.load(job_id)
        job.events.append(event)
        self.save(job)

    def set_status(self, job_id: str, status: Literal["queued", "running", "completed", "failed"]) -> None:
        job = self.load(job_id)
        job.status = status
        self.save(job)

    def complete(self, job_id: str, report: dict[str, Any]) -> None:
        job = self.load(job_id)
        job.status = "completed"
        job.report = report
        self.save(job)

    def fail(self, job_id: str, message: str, code: str = "JOB_FAILED") -> None:
        job = self.load(job_id)
        job.status = "failed"
        job.error = {"message": message, "code": code}
        self.save(job)
```

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/api/test_jobs.py -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/math_variant/api/jobs.py tests/unit/api/test_jobs.py
git commit -m "feat: add thread-safe generation job store"
```

---

## Task 7: 파이프라인 결과 → RunStore 어댑터

**Files:**
- Create: `src/math_variant/api/adapters.py`
- Create: `tests/unit/api/test_adapters.py`

**Step 1: 실패 테스트 작성**

`tests/unit/api/test_adapters.py`:
```python
"""T08 — PipelineReport → RunStore 형식 변환 어댑터 테스트."""

from __future__ import annotations

import json

from math_variant.agents.pipeline import CandidateVerdict, PipelineReport
from math_variant.api.adapters import report_to_run_store
from math_variant.domain.candidate import CandidateProblem
from math_variant.verifiers.test_runner import TestVerdict, VerificationOutcome
from math_variant.sandbox.contracts import SandboxStatus
from math_variant.services.blind_solver import BlindConsensus
from math_variant.agents.schemas import CodeReviewOutput, CriticOutput, PlannerOutput


def _planner() -> PlannerOutput:
    return PlannerOutput.model_validate(
        {
            "core_concepts": ["포물선"],
            "auxiliary_concepts": [],
            "objective": "a의 값",
            "answer_type": "expression",
            "domain": "도형의 방정식",
            "preservation_goals": ["평행이동"],
            "strategy": {
                "difficulty_target": "중상",
                "preservation_goals": ["평행이동"],
                "variation_direction": ["질문 역전"],
                "quality_criteria": ["유일해"],
            },
            "unresolved_assumptions": [],
        }
    )


def _pass_verdict() -> CandidateVerdict:
    candidate = CandidateProblem(
        candidate_id="cand-1",
        plan_id="plan-1",
        problem_text="문제 본문",
        formalization={"symbols": ["x"], "constraints": [], "goal": "a"},
        final_answer_claim="8sqrt(2)",
        solution_steps=[{"step_id": "s1", "statement": "단계"}],
        transformation_evidence=[{"dimension": "objective", "description": "역전"}],
    )
    candidate.mark_verified("PASS", "run-1:sandbox-test")
    return CandidateVerdict(
        candidate=candidate,
        blueprint_title="질문 역전",
        code_review=CodeReviewOutput(verdict="APPROVE", safe=True, test_consistent=True),
        test_outcome=VerificationOutcome(
            verdict=TestVerdict.PASS,
            status=SandboxStatus.COMPLETED,
            detail="통과",
        ),
        blind_consensus=BlindConsensus(status="PASS", solver_a="A", solver_b="B"),
        critic=CriticOutput(score=8.0, difficulty_estimate="중상", recommendation="PASS"),
        status="PASS",
    )


def test_report_to_run_store_maps_candidates(tmp_path) -> None:
    report = PipelineReport(
        run_id="run-1",
        planner=_planner(),
        ideas=[],
        adopted_ideas=[],
        candidates=[_pass_verdict()],
        ranking=[],
    )
    data = report_to_run_store(report)
    assert data["run_id"] == "run-1"
    assert data["state"] == "GENERATED"
    assert len(data["candidates"]) == 1
    candidate = data["candidates"][0]
    assert candidate["verification_status"] == "PASS"
    assert candidate["validation_ref"] == "run-1:sandbox-test"
    # 검토 화면(hasRequiredArtifacts)이 요구하는 산출물이 모두 있다
    assert candidate["solution_steps"]
    assert candidate["transformation_evidence"]
    assert candidate["rubric"]["items"]
    assert candidate["evidence"]["checks"]
    assert candidate["blueprint_title"] == "질문 역전"
    assert candidate["critic_score"] == 8.0
    # JSON 직렬화 가능 (RunStore.save_run 호환)
    json.dumps(data, ensure_ascii=False)


def test_report_to_run_store_non_pass_keeps_status(tmp_path) -> None:
    verdict = _pass_verdict()
    verdict.candidate.mark_verified("FAIL", "run-1")
    verdict.status = "FAIL"  # type: ignore[assignment]
    report = PipelineReport(
        run_id="run-2", planner=_planner(), ideas=[], adopted_ideas=[], candidates=[verdict]
    )
    data = report_to_run_store(report)
    assert data["candidates"][0]["verification_status"] == "FAIL"
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/api/test_adapters.py -v`
Expected: FAIL — 모듈 없음.

**Step 3: 구현**

`src/math_variant/api/adapters.py`:
```python
"""PipelineReport → RunStore 형식 변환 어댑터 (T08).

기존 검토 화면(public_run)은 verification_status=="PASS" + 필수 산출물(rubric, evidence)을
요구하므로, 파이프라인 후보를 그 형식에 맞춰 합성한다:
- rubric: 생성기의 solution_steps → RubricItem (score=1/단계)
- evidence: test_outcome(샌드박스) + blind_consensus → CheckResult
- critic 점수·코드리뷰 판정은 후보 메타데이터로 노출
"""

from __future__ import annotations

from typing import Any

from math_variant.agents.pipeline import PipelineReport
from math_variant.domain.candidate import VerificationStatus


def report_to_run_store(report: PipelineReport) -> dict[str, Any]:
    """파이프라인 리포트를 RunStore 가 읽는 run JSON 으로 변환한다."""
    return {
        "run_id": report.run_id,
        "state": "GENERATED",
        "candidates": [_candidate_to_dict(v) for v in report.candidates],
        "created_at": report.created_at.isoformat(),
        "updated_at": report.created_at.isoformat(),
    }


def _candidate_to_dict(verdict) -> dict[str, Any]:
    candidate = verdict.candidate
    status: VerificationStatus = candidate.verification_status
    if verdict.test_outcome is not None:
        status = "PASS" if verdict.test_outcome.passes else "FAIL"
        candidate.mark_verified(status, f"{verdict.candidate.candidate_id}:sandbox-test")
    checks: list[dict[str, Any]] = []
    if verdict.test_outcome is not None:
        checks.append(
            {
                "check_id": f"{candidate.candidate_id}-sandbox",
                "kind": "sandbox",
                "status": "PASS" if verdict.test_outcome.passes else "FAIL",
                "critical": True,
                "evidence": {"detail": verdict.test_outcome.detail},
            }
        )
    if verdict.blind_consensus is not None:
        checks.append(
            {
                "check_id": f"{candidate.candidate_id}-blind",
                "kind": "blind",
                "status": verdict.blind_consensus.status,
                "critical": False,
                "evidence": {"reason": verdict.blind_consensus.reason},
            }
        )
    return {
        "candidate_id": candidate.candidate_id,
        "plan_id": candidate.plan_id,
        "problem_text": candidate.problem_text,
        "formalization": candidate.formalization.model_dump(mode="json"),
        "final_answer_claim": candidate.final_answer_claim,
        "solution_steps": [s.model_dump(mode="json") for s in candidate.solution_steps],
        "transformation_evidence": candidate.transformation_evidence,
        "verification_status": status,
        "validation_ref": candidate.validation_ref,
        "blueprint_title": verdict.blueprint_title,
        "critic_score": verdict.critic.score if verdict.critic else None,
        "code_review_verdict": verdict.code_review.verdict if verdict.code_review else None,
        "rubric": {
            "graph_id": f"{candidate.candidate_id}-rubric",
            "items": [
                {
                    "node_id": step.step_id,
                    "score": 1,
                    "description": step.statement,
                }
                for step in candidate.solution_steps
            ],
            "total_points": float(len(candidate.solution_steps)),
            "derived_from_verified": status == "PASS",
        },
        "evidence": {
            "evidence_id": f"{candidate.candidate_id}-evidence",
            "candidate_id": candidate.candidate_id,
            "checks": checks,
        },
    }
```

> 참고: `derived_from_verified=True`는 Rubric validator가 강제한다. `status=="PASS"`일 때만 True로 설정하고, 그 외는 검토 화면에 노출되지 않으므로 무관하다. `public_run()`이 PASS 후보만 노출하므로 FAIL 후보의 rubric/evidence는 화면에 안 보이지만 파일에는 남는다.

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/api/test_adapters.py -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/math_variant/api/adapters.py tests/unit/api/test_adapters.py
git commit -m "feat: adapt pipeline report to run store schema for review screen"
```

---

## Task 8: API 엔드포인트 — 생성 작업 + SSE + 문제 라이브러리

**Files:**
- Modify: `src/math_variant/api/app.py`
- Create: `tests/unit/api/test_generation_api.py`
- Create: `tests/unit/api/test_problems_api.py`

**Step 1: 실패 테스트 작성**

`tests/unit/api/test_generation_api.py`:
```python
"""T08 — 생성 작업 API 테스트 (fake 파이프라인 팩토리 사용)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from math_variant.api import app as api_module


class _FakeRunner:
    """실제 LLM 없이 즉시 이벤트를 방출하고 완료하는 러너."""

    def __init__(self) -> None:
        self.started: list[dict[str, Any]] = []
        self.cancel: bool = False

    def start(self, job_id: str, source_text: str, options: dict[str, Any]) -> None:
        self.started.append({"job_id": job_id, "source_text": source_text, "options": options})
        from math_variant.api.jobs import JobStore
        from math_variant.events import EventStage, PipelineEvent
        from datetime import UTC, datetime

        store = api_module._default_jobs()
        store.set_status(job_id, "running")
        store.append_event(
            job_id,
            PipelineEvent(
                event_id="e1", type="stage", stage=EventStage.PLANNER,
                status="done", message="기획 완료", ts=datetime.now(UTC),
            ),
        )
        store.append_event(
            job_id,
            PipelineEvent(
                event_id="e2", type="llm_call", stage=EventStage.PLANNER,
                status="done", ts=datetime.now(UTC),
                data={"role": "planner", "schema": "PlannerOutput", "provider": "fake",
                      "model": "m", "temperature": 0.2, "attempts": 1,
                      "latency_ms": 5, "cost_usd": 0.0, "ok": True,
                      "summary": {"core_concepts": ["포물선"]}, "error": None},
            ),
        )
        store.complete(job_id, {"run_id": job_id, "candidates": 1})


@pytest.fixture()
def client(tmp_path: Path, monkeypatch) -> TestClient:
    api_module._store = None
    api_module._jobs = None
    api_module._problems = None
    api_module._runner = _FakeRunner()
    monkeypatch.setattr(api_module, "_store", __import__("math_variant.api.storage", fromlist=["RunStore"]).RunStore(tmp_path / "runs"))
    monkeypatch.setattr(api_module, "_jobs", __import__("math_variant.api.jobs", fromlist=["JobStore"]).JobStore(tmp_path / "jobs"))
    monkeypatch.setattr(api_module, "_problems", __import__("math_variant.api.problems", fromlist=["ProblemStore"]).ProblemStore(tmp_path / "problems"))
    api_module._reset_active_job()
    return TestClient(api_module.app)


def test_create_generation_returns_job(client: TestClient) -> None:
    response = client.post(
        "/api/generations",
        json={"source": {"mode": "text", "text": "포물선 y=x^2 의 접선"}, "options": {}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["run_id"] == body["job_id"]
    # 백그라운드 러너가 동기 실행됐는지(테스트용) 확인
    job = client.get(f"/api/generations/{body['job_id']}").json()
    assert job["status"] in {"running", "completed"}


def test_create_generation_requires_source_text(client: TestClient) -> None:
    response = client.post(
        "/api/generations",
        json={"source": {"mode": "text", "text": "   "}, "options": {}},
    )
    assert response.status_code == 422


def test_create_generation_concurrent_rejected(client: TestClient) -> None:
    client.post(
        "/api/generations",
        json={"source": {"mode": "text", "text": "첫번째"}, "options": {}},
    )
    # active job 이 남아있으면 409
    api_module._active_job_id = "run-stale"
    response = client.post(
        "/api/generations",
        json={"source": {"mode": "text", "text": "두번째"}, "options": {}},
    )
    assert response.status_code == 409


def test_generation_events_sse(client: TestClient) -> None:
    created = client.post(
        "/api/generations",
        json={"source": {"mode": "text", "text": "원문"}, "options": {}},
    ).json()
    with client.stream("GET", f"/api/generations/{created['job_id']}/events") as stream:
        lines = "".join(stream.iter_text())
    assert "planner" in lines
    assert "llm_call" in lines


def test_generation_from_problem_source(client: TestClient) -> None:
    problem = client.post("/api/problems", json={"text": "원문제", "title": "T1"}).json()
    response = client.post(
        "/api/generations",
        json={"source": {"mode": "problem", "problem_id": problem["problem_id"]}, "options": {}},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_generation_missing_problem_404(client: TestClient) -> None:
    response = client.post(
        "/api/generations",
        json={"source": {"mode": "problem", "problem_id": "problem-nope"}, "options": {}},
    )
    assert response.status_code == 404
```

`tests/unit/api/test_problems_api.py`:
```python
"""T08 — 문제 라이브러리 API 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from math_variant.api import app as api_module
from math_variant.api.problems import ProblemStore


@pytest.fixture()
def client(tmp_path: Path, monkeypatch) -> TestClient:
    api_module._store = None
    api_module._jobs = None
    api_module._problems = None
    api_module._runner = None
    monkeypatch.setattr(api_module, "_problems", ProblemStore(tmp_path / "problems"))
    monkeypatch.setattr(
        api_module, "_store",
        __import__("math_variant.api.storage", fromlist=["RunStore"]).RunStore(tmp_path / "runs"),
    )
    api_module._reset_active_job()
    return TestClient(api_module.app)


def test_register_and_list_problems(client: TestClient) -> None:
    created = client.post("/api/problems", json={"text": "포물선 y=x^2", "title": "T"}).json()
    assert created["source"] == "manual"
    listed = client.get("/api/problems").json()
    assert len(listed) == 1
    assert listed[0]["problem_id"] == created["problem_id"]


def test_register_duplicate_returns_same(client: TestClient) -> None:
    first = client.post("/api/problems", json={"text": "본문 A"}).json()
    second = client.post("/api/problems", json={"text": "본문 A"}).json()
    assert first["problem_id"] == second["problem_id"]


def test_delete_problem(client: TestClient) -> None:
    created = client.post("/api/problems", json={"text": "삭제할 문제"}).json()
    response = client.delete(f"/api/problems/{created['problem_id']}")
    assert response.status_code == 204
    assert client.get("/api/problems").json() == []


def test_approved_lists_approved_only(client: TestClient) -> None:
    client.post("/api/problems", json={"text": "직접 등록"})
    client.post("/api/problems", json={"text": "승인 문제", "source": "approved", "source_run_id": "run-1"})
    approved = client.get("/api/approved").json()
    assert len(approved) == 1
    assert approved[0]["source_run_id"] == "run-1"
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/api/test_generation_api.py tests/unit/api/test_problems_api.py -v`
Expected: FAIL — `app.py`에 엔드포인트·`_runner`·`_reset_active_job` 없음.

**Step 3: 구현**

`src/math_variant/api/app.py` — 다음을 추가한다.

- 모듈 레벨 상태·의존성 주입:
```python
from concurrent.futures import Future
from threading import Lock
from typing import Any, Protocol

from math_variant.api.adapters import report_to_run_store
from math_variant.api.jobs import CreateOptions, GenerationJob, JobStore
from math_variant.api.problems import Problem, ProblemStore

_store: RunStore | None = None
_jobs: JobStore | None = None
_problems: ProblemStore | None = None
_active_job_id: str | None = None
_active_job_lock = Lock()
_runner: Runner | None = None


class Runner(Protocol):
    """백그라운드 생성 작업 실행자 계약 (테스트에서 fake 로 대체)."""

    def start(self, job_id: str, source_text: str, options: dict[str, Any]) -> None: ...


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
        _runner = PipelineRunner(_default_jobs(), _default_store(), _default_problems())
    return _runner


def _reset_active_job() -> None:
    global _active_job_id
    _active_job_id = None
```

- `PipelineRunner` (백그라운드 스레드 실행):
```python
class PipelineRunner:
    """JobStore 에 이벤트를 기록하면서 파이프라인을 백그라운드로 실행한다."""

    def __init__(
        self,
        jobs: JobStore,
        store: RunStore,
        problems: ProblemStore,
        sandbox_image: str = "math-variant-sandbox:test",
    ) -> None:
        self.jobs = jobs
        self.store = store
        self.problems = problems
        self.sandbox_image = sandbox_image

    def start(self, job_id: str, source_text: str, options: dict[str, Any]) -> None:
        import threading

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

        self.jobs.set_status(job_id, "running")
        try:
            pipeline = build_agent_pipeline(
                source_text=source_text,
                difficulty_target=options.get("difficulty_target", ""),
                ideator_count=int(options.get("ideator_count", 3)),
                max_refine=int(options.get("max_refine", 2)),
                on_event=lambda event: self.jobs.append_event(job_id, event),
                runs_dir=Path("runs"),
                figures_dir=Path("runs") / "figures",
                sandbox_image=self.sandbox_image,
            )
            report = pipeline.run(normalize_source(source_text))
        except MathVariantError as exc:
            self.jobs.fail(job_id, exc.error.message, exc.code.value)
            return
        except Exception as exc:  # noqa: BLE001 - 러너에서 어떤 실패도 job 에 남긴다
            self.jobs.fail(job_id, str(exc)[:500])
            return
        run_data = report_to_run_store(report)
        self.store.save_run(report.run_id, run_data)
        self.jobs.complete(job_id, {"run_id": report.run_id, "candidates": len(report.candidates)})
        _clear_active(job_id)
```

- active job 관리:
```python
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
```

- Pydantic 요청 모델:
```python
class SourcePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["text", "problem"] = "text"
    text: str | None = None
    problem_id: str | None = None


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: SourcePayload
    options: dict[str, Any] = Field(default_factory=dict)


class ProblemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1)
    title: str = ""
    source: Literal["manual", "approved"] = "manual"
    source_run_id: str | None = None
```

- 엔드포인트:
```python
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
    options = CreateOptions.model_validate(payload.options)
    job = _default_jobs().create(text, options, source_mode=source.mode, source_label=label)
    _set_active(job.job_id)
    _default_runner().start(job.job_id, text, options.model_dump())
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
        job = _default_jobs().load(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def event_source():
        from datetime import UTC, datetime
        last_index = 0
        while True:
            current = _default_jobs().load(job_id)
            events = current.events
            while last_index < len(events):
                event = events[last_index]
                yield f"data: {event.model_dump_json()}\n\n"
                last_index += 1
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
def list_problems() -> list[dict[str, Any]]:
    return [p.model_dump(mode="json") for p in _default_problems().list()]


@app.post("/api/problems")
def register_problem(payload: ProblemRequest) -> dict[str, Any]:
    problem = _default_problems().register(
        payload.text, title=payload.title, source=payload.source, source_run_id=payload.source_run_id
    )
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
```

- 승인 자동 등록: 기존 `decide` 엔드포인트의 `approved` 분기에서 문제 라이브러리에 자동 등록:
```python
    event = _default_store().apply_decision(...)
    if payload.decision == "approved":
        candidate_data = next(
            (c for c in _default_store().load_run(run_id).get("candidates", [])
             if c.get("candidate_id") == candidate_id),
            None,
        )
        if candidate_data and candidate_data.get("problem_text"):
            _default_problems().register(
                candidate_data["problem_text"],
                title=f"{run_id} {candidate_id}",
                source="approved",
                source_run_id=run_id,
            )
```

- import 추가: `import asyncio`, `from fastapi.responses import StreamingResponse`, `from typing import Literal`.

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/api/test_generation_api.py tests/unit/api/test_problems_api.py -v`
Expected: PASS

> SSE 테스트에서 `client.stream(...)`로 끝까지 읽으려면 job이 완료 상태여야 한다. Fake runner는 동기로 완료 처리하므로 바로 종료된다. 실제 `PipelineRunner`는 스레드이므로 SSE가 0.5s 폴링으로 종료 감지한다.

**Step 5: 커밋**

```bash
git add src/math_variant/api/app.py tests/unit/api/test_generation_api.py tests/unit/api/test_problems_api.py
git commit -m "feat: add generation job and problem library API endpoints"
```

---

## Task 9: 프론트 타입·API 클라이언트 확장

**Files:**
- Modify: `web/src/lib/types.ts`
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/lib/api.test.ts`

> Next.js 16 주의: `web/AGENTS.md` 지침에 따라 코드 작성 전 `node_modules/next/dist/docs/`의 관련 문서(App Router, use client)를 확인한다. 클라이언트 컴포넌트는 `"use client"` 지시어를 사용한다.

**Step 1: 실패 테스트 작성**

`web/src/lib/api.test.ts`에 추가:
```ts
import { createGeneration, getJob, listApproved, listProblems, registerProblem } from "./api";
import type { Problem } from "./types";

function makeProblem(overrides: Partial<Problem> = {}): Problem {
  return {
    problem_id: "problem-1",
    title: "T",
    text: "본문",
    source: "manual",
    source_run_id: null,
    created_at: "2026-01-01T00:00:00+00:00",
    ...overrides,
  };
}

describe("생성 작업·문제 라이브러리 API (T08)", () => {
  it("createGeneration 은 POST 를 보내고 결과를 반환한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ job_id: "run-1", run_id: "run-1", status: "queued" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock);

    const result = await createGeneration(
      { mode: "text", text: "원문" },
      { difficulty_target: "중상", ideator_count: 3, max_refine: 2 },
    );
    expect(result.job_id).toBe("run-1");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/generations"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("getJob 은 작업 상태와 이벤트를 반환한다", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          job_id: "run-1",
          run_id: "run-1",
          status: "completed",
          events: [],
          error: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const job = await getJob("run-1");
    expect(job.status).toBe("completed");
  });

  it("문제 라이브러리 CRUD 가 동작한다", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([makeProblem()]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const problems = await listProblems();
    expect(problems).toHaveLength(1);

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(makeProblem()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const created = await registerProblem("새 문제");
    expect(created.problem_id).toBe("problem-1");

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([makeProblem({ source: "approved" })]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const approved = await listApproved();
    expect(approved[0]?.source).toBe("approved");
  });
});
```

**Step 2: 테스트 실행 (실패 확인)**

Run (workdir `web`): `npm run test`
Expected: FAIL — 함수·타입 없음.

**Step 3: 구현**

`web/src/lib/types.ts` 추가:
```ts
/** 생성 작업·문제 라이브러리 (T08). */

export type JobStatus = "queued" | "running" | "completed" | "failed";

export type JobEventType = "stage" | "llm_call";

export type JobEventStatus = "started" | "done" | "failed";

export interface JobEvent {
  event_id: string;
  type: JobEventType;
  stage: string;
  status: JobEventStatus;
  message: string;
  candidate_id?: string | null;
  ts: string;
  data: Record<string, unknown>;
}

export interface CreateOptions {
  difficulty_target: string;
  ideator_count: number;
  max_refine: number;
}

export interface SourcePayload {
  mode: "text" | "problem";
  text?: string | null;
  problem_id?: string | null;
}

export interface GenerationResult {
  job_id: string;
  run_id: string;
  status: JobStatus;
}

export interface GenerationJob {
  job_id: string;
  run_id: string;
  source: { mode: string; text: string; label?: string };
  options: CreateOptions;
  status: JobStatus;
  events: JobEvent[];
  error?: { message: string; code: string } | null;
  report?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface Problem {
  problem_id: string;
  title: string;
  text: string;
  source: "manual" | "approved";
  source_run_id?: string | null;
  created_at: string;
}

export interface ProblemRequest {
  text: string;
  title?: string;
  source?: "manual" | "approved";
  source_run_id?: string | null;
}
```

`web/src/lib/api.ts` 추가:
```ts
import type { CreateOptions, GenerationJob, GenerationResult, Problem, ProblemRequest, SourcePayload } from "./types";

export async function createGeneration(
  source: SourcePayload,
  options: CreateOptions,
): Promise<GenerationResult> {
  return requestJson<GenerationResult>("/api/generations", {
    method: "POST",
    body: JSON.stringify({ source, options }),
  });
}

export async function getJob(jobId: string): Promise<GenerationJob> {
  return requestJson<GenerationJob>(`/api/generations/${jobId}`);
}

export function streamJobEvents(
  jobId: string,
  handlers: {
    onEvent: (event: JobEvent) => void;
    onDone: (status: JobStatus) => void;
    onError: (message: string) => void;
  },
): () => void {
  const source = new EventSource(`${API_BASE}/api/generations/${jobId}/events`);
  source.addEventListener("done", (event) => {
    handlers.onDone((event as MessageEvent).data as JobStatus);
    source.close();
  });
  source.onmessage = (event) => {
    try {
      handlers.onEvent(JSON.parse(event.data) as JobEvent);
    } catch {
      /* 비정상 프레임 무시 */
    }
  };
  source.onerror = () => {
    handlers.onError("진행 스트림 연결이 끊어졌습니다");
    source.close();
  };
  return () => source.close();
}

export async function listProblems(): Promise<Problem[]> {
  return requestJson<Problem[]>("/api/problems");
}

export async function registerProblem(payload: ProblemRequest): Promise<Problem> {
  return requestJson<Problem>("/api/problems", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteProblem(problemId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/problems/${problemId}`, { method: "DELETE" });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API 오류 ${response.status}: ${body.slice(0, 200)}`);
  }
}

export async function listApproved(): Promise<Problem[]> {
  return requestJson<Problem[]>("/api/approved");
}
```
(`JobEvent`, `JobStatus` import 추가)

**Step 4: 테스트 실행 (통과 확인)**

Run (workdir `web`): `npm run test`
Expected: PASS

**Step 5: 타입·린트 확인**

Run (workdir `web`): `npm run typecheck; npm run lint`
Expected: 통과

**Step 6: 커밋**

```bash
git add web/src/lib/types.ts web/src/lib/api.ts web/src/lib/api.test.ts
git commit -m "feat: extend web client for generation jobs and problem library"
```

---

## Task 10: 생성 화면 + 문제 선택기 (CreateForm, ProblemPicker)

**Files:**
- Create: `web/src/app/create/page.tsx`
- Create: `web/src/components/CreateForm.tsx`
- Create: `web/src/components/ProblemPicker.tsx`
- Create: `web/src/components/__tests__/CreateForm.test.tsx`
- Create: `web/src/components/__tests__/ProblemPicker.test.tsx`

**Step 1: 실패 테스트 작성**

`web/src/components/__tests__/CreateForm.test.tsx`:
```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CreateForm } from "../CreateForm";
import * as api from "@/lib/api";

describe("CreateForm (T08 생성 화면)", () => {
  it("텍스트 모드에서 생성 시작을 요청한다", async () => {
    const push = vi.fn();
    vi.spyOn(api, "createGeneration").mockResolvedValue({
      job_id: "run-1",
      run_id: "run-1",
      status: "queued",
    });
    vi.spyOn(api, "listProblems").mockResolvedValue([]);

    render(<CreateForm onNavigate={push} />);

    await userEvent.type(screen.getByLabelText(/문제 본문/), "포물선 y=x^2 의 접선");
    await userEvent.click(screen.getByRole("button", { name: /생성 시작/ }));

    await waitFor(() => {
      expect(api.createGeneration).toHaveBeenCalledWith(
        expect.objectContaining({ mode: "text", text: "포물선 y=x^2 의 접선" }),
        expect.objectContaining({ ideator_count: 3 }),
      );
    });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/runs/run-1/progress"));
  });

  it("빈 텍스트면 생성하지 않는다", async () => {
    vi.spyOn(api, "listProblems").mockResolvedValue([]);
    const create = vi.spyOn(api, "createGeneration").mockResolvedValue({
      job_id: "r", run_id: "r", status: "queued",
    });
    render(<CreateForm onNavigate={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /생성 시작/ }));
    expect(create).not.toHaveBeenCalled();
  });
});
```

`web/src/components/__tests__/ProblemPicker.test.tsx`:
```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProblemPicker } from "../ProblemPicker";
import * as api from "@/lib/api";

describe("ProblemPicker (T08)", () => {
  it("검색어로 문제를 필터링해 선택할 수 있다", async () => {
    vi.spyOn(api, "listProblems").mockResolvedValue([
      { problem_id: "p1", title: "포물선", text: "포물선 문제", source: "manual", source_run_id: null, created_at: "" },
      { problem_id: "p2", title: "직선", text: "직선 문제", source: "manual", source_run_id: null, created_at: "" },
    ]);
    const onSelect = vi.fn();
    render(<ProblemPicker value="" onSelect={onSelect} />);
    await waitFor(() => expect(screen.getByRole("combobox")).toBeInTheDocument());
    await userEvent.type(screen.getByPlaceholderText(/검색/), "포물선");
    await userEvent.click(screen.getByText("포물선 문제"));
    expect(onSelect).toHaveBeenCalledWith("p1");
  });
});
```

**Step 2: 테스트 실행 (실패 확인)**

Run (workdir `web`): `npm run test`
Expected: FAIL — 컴포넌트 없음.

**Step 3: 구현**

`web/src/components/ProblemPicker.tsx`:
```tsx
"use client";

import { useEffect, useMemo, useState } from "react";

import { listProblems } from "@/lib/api";
import type { Problem } from "@/lib/types";

/** 문제 라이브러리 선택 드롭다운 (검색 포함). */
export function ProblemPicker({
  value,
  onSelect,
}: {
  value: string;
  onSelect: (problemId: string) => void;
}) {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    listProblems()
      .then((data) => {
        if (!cancelled) {
          setProblems(data);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) {
      return problems;
    }
    return problems.filter((p) => `${p.title} ${p.text}`.toLowerCase().includes(keyword));
  }, [problems, query]);

  return (
    <div className="problem-picker">
      <input
        type="search"
        placeholder="문제 검색"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="문제 검색"
      />
      <select
        value={value}
        onChange={(e) => onSelect(e.target.value)}
        aria-label="문제 선택"
        data-testid="problem-select"
      >
        <option value="">문제를 선택하세요</option>
        {filtered.map((problem) => (
          <option key={problem.problem_id} value={problem.problem_id}>
            {problem.title || problem.problem_id} — {problem.text.slice(0, 40)}
          </option>
        ))}
      </select>
    </div>
  );
}
```

`web/src/components/CreateForm.tsx`:
```tsx
"use client";

import { useState } from "react";
import Link from "next/link";

import { createGeneration } from "@/lib/api";
import { ProblemPicker } from "./ProblemPicker";

const DIFFICULTIES = ["", "중", "중상", "상"];
const IDEATOR_COUNTS = [1, 2, 3, 4, 5];
const REFINE_COUNTS = [0, 1, 2, 3];

/** 생성 화면 폼 — 원문제 입력(텍스트/라이브러리) + 생성 옵션. */
export function CreateForm({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [mode, setMode] = useState<"text" | "problem">("text");
  const [text, setText] = useState("");
  const [problemId, setProblemId] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [ideatorCount, setIdeatorCount] = useState(3);
  const [maxRefine, setMaxRefine] = useState(2);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    !submitting && (mode === "text" ? text.trim().length > 0 : problemId !== "");

  const handleSubmit = async () => {
    if (!canSubmit) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const source =
        mode === "text" ? { mode: "text" as const, text: text.trim() } : { mode: "problem" as const, problem_id: problemId };
      const result = await createGeneration(source, {
        difficulty_target: difficulty,
        ideator_count: ideatorCount,
        max_refine: maxRefine,
      });
      onNavigate(`/runs/${result.run_id}/progress`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
      setSubmitting(false);
    }
  };

  return (
    <div className="create-form">
      <fieldset className="create-source">
        <legend>원문제 입력</legend>
        <div className="create-mode-row">
          <label>
            <input type="radio" checked={mode === "text"} onChange={() => setMode("text")} />
            텍스트 붙여넣기
          </label>
          <label>
            <input type="radio" checked={mode === "problem"} onChange={() => setMode("problem")} />
            기존 문제에서 선택
          </label>
        </div>
        {mode === "text" ? (
          <textarea
            aria-label="문제 본문"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="변형할 원문제 본문을 붙여넣으세요"
            rows={8}
          />
        ) : (
          <ProblemPicker value={problemId} onSelect={setProblemId} />
        )}
      </fieldset>

      <fieldset className="create-options">
        <legend>생성 옵션</legend>
        <label>
          난이도 목표
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            {DIFFICULTIES.map((level) => (
              <option key={level || "default"} value={level}>
                {level || "자동"}
              </option>
            ))}
          </select>
        </label>
        <label>
          발상 개수
          <select value={ideatorCount} onChange={(e) => setIdeatorCount(Number(e.target.value))}>
            {IDEATOR_COUNTS.map((count) => (
              <option key={count} value={count}>
                {count}
              </option>
            ))}
          </select>
        </label>
        <label>
          개선 횟수
          <select value={maxRefine} onChange={(e) => setMaxRefine(Number(e.target.value))}>
            {REFINE_COUNTS.map((count) => (
              <option key={count} value={count}>
                {count}
              </option>
            ))}
          </select>
        </label>
      </fieldset>

      {error && <p className="create-error">{error}</p>}

      <div className="create-actions">
        <Link className="create-cancel" href="/">
          취소
        </Link>
        <button
          type="button"
          className="button-create"
          onClick={handleSubmit}
          disabled={!canSubmit}
        >
          {submitting ? "생성 중…" : "생성 시작"}
        </button>
      </div>
    </div>
  );
}
```

`web/src/app/create/page.tsx`:
```tsx
import type { Metadata } from "next";
import { useRouter } from "next/navigation";

import { CreateForm } from "@/components/CreateForm";

export const metadata: Metadata = {
  title: "새 문제 생성",
};

export default function CreatePage() {
  const router = useRouter();
  return (
    <main className="create-page">
      <div className="page-frame">
        <header className="create-header">
          <p className="create-eyebrow">
            <Link href="/">← 실행 목록</Link>
          </p>
          <h1>새 문제 만들기</h1>
          <p className="create-sub">
            원문제를 입력하거나 라이브러리에서 선택하면 다중 에이전트 파이프라인이 새 문항을 제작합니다.
          </p>
        </header>
        <CreateForm onNavigate={(path) => router.push(path)} />
      </div>
    </main>
  );
}
```
> `useRouter` 사용 시 `Link` import 추가: `import Link from "next/link";`

**Step 4: 테스트 실행 (통과 확인)**

Run (workdir `web`): `npm run test`
Expected: PASS

**Step 5: 타입·린트**

Run (workdir `web`): `npm run typecheck; npm run lint`
Expected: 통과

**Step 6: 커밋**

```bash
git add web/src/app/create web/src/components/CreateForm.tsx web/src/components/ProblemPicker.tsx web/src/components/__tests__/CreateForm.test.tsx web/src/components/__tests__/ProblemPicker.test.tsx
git commit -m "feat: add create page with problem picker and options"
```

---

## Task 11: 진행 화면 (ProgressView, CallLog — SSE)

**Files:**
- Create: `web/src/app/runs/[runId]/progress/page.tsx`
- Create: `web/src/app/runs/[runId]/progress/ProgressClient.tsx`
- Create: `web/src/components/ProgressView.tsx`
- Create: `web/src/components/CallLog.tsx`
- Create: `web/src/components/__tests__/ProgressView.test.tsx`
- Create: `web/src/components/__tests__/CallLog.test.tsx`

**Step 1: 실패 테스트 작성**

`web/src/components/__tests__/ProgressView.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProgressView } from "../ProgressView";
import * as api from "@/lib/api";

function makeEvent(overrides = {}) {
  return {
    event_id: "e1",
    type: "stage",
    stage: "planner",
    status: "done",
    message: "기획 완료",
    ts: "2026-01-01T00:00:00+00:00",
    data: {},
    ...overrides,
  };
}

describe("ProgressView (T08)", () => {
  it("완료된 job 은 검토 화면 링크를 보여준다", () => {
    vi.spyOn(api, "getJob").mockResolvedValue({
      job_id: "run-1",
      run_id: "run-1",
      source: { mode: "text", text: "원문" },
      options: { difficulty_target: "", ideator_count: 3, max_refine: 2 },
      status: "completed",
      events: [makeEvent()],
      error: null,
      created_at: "",
      updated_at: "",
    } as never);
    vi.spyOn(api, "streamJobEvents").mockImplementation((_jobId, handlers) => {
      handlers.onDone("completed");
      return () => {};
    });

    render(<ProgressView jobId="run-1" />);
    expect(screen.getByRole("link", { name: /검토 화면으로 이동/ })).toHaveAttribute(
      "href",
      "/runs/run-1/review",
    );
  });

  it("실패한 job 은 에러 배너를 보여준다", () => {
    vi.spyOn(api, "getJob").mockResolvedValue({
      job_id: "run-1",
      run_id: "run-1",
      source: { mode: "text", text: "원문" },
      options: { difficulty_target: "", ideator_count: 3, max_refine: 2 },
      status: "failed",
      events: [],
      error: { message: "boom", code: "AGENT_UNRESOLVED" },
      created_at: "",
      updated_at: "",
    } as never);
    vi.spyOn(api, "streamJobEvents").mockImplementation((_jobId, handlers) => {
      handlers.onError("연결 끊김");
      return () => {};
    });

    render(<ProgressView jobId="run-1" />);
    expect(screen.getByText(/boom/)).toBeInTheDocument();
  });
});
```

`web/src/components/__tests__/CallLog.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CallLog } from "../CallLog";
import type { JobEvent } from "@/lib/types";

describe("CallLog (T08)", () => {
  it("LLM 호출 이벤트를 모델·요약과 함께 렌더링한다", () => {
    const events: JobEvent[] = [
      {
        event_id: "e1",
        type: "llm_call",
        stage: "ideation",
        status: "done",
        message: "",
        ts: "2026-01-01T00:00:00+00:00",
        data: { role: "ideator", schema: "IdeationOutput", provider: "deepseek", model: "deepseek-v4-flash", ok: true, summary: { title: "질문 역전" }, latency_ms: 100, cost_usd: 0.001 },
      },
    ];
    render(<CallLog events={events} />);
    expect(screen.getByText("deepseek-v4-flash")).toBeInTheDocument();
    expect(screen.getByText("질문 역전")).toBeInTheDocument();
  });

  it("실패 이벤트는 오류 코드를 표시한다", () => {
    const events: JobEvent[] = [
      {
        event_id: "e2",
        type: "llm_call",
        stage: "judge",
        status: "failed",
        message: "",
        ts: "",
        data: { role: "judge", schema: "JudgeOutput", provider: "deepseek", model: "m", ok: false, error: { code: "SCHEMA_VALIDATION" } },
      },
    ];
    render(<CallLog events={events} />);
    expect(screen.getByText("SCHEMA_VALIDATION")).toBeInTheDocument();
  });
});
```

**Step 2: 테스트 실행 (실패 확인)**

Run (workdir `web`): `npm run test`
Expected: FAIL — 컴포넌트 없음.

**Step 3: 구현**

`web/src/components/CallLog.tsx`:
```tsx
import type { JobEvent } from "@/lib/types";

function formatTime(ts: string): string {
  if (!ts) {
    return "";
  }
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleTimeString("ko-KR", { hour12: false });
}

/** LLM 호출 로그 — 호출된 LLM·결과 요약·지연·비용. */
export function CallLog({ events }: { events: JobEvent[] }) {
  const calls = events.filter((event) => event.type === "llm_call");
  if (calls.length === 0) {
    return <p className="call-log-empty">아직 LLM 호출이 없습니다.</p>;
  }
  return (
    <ol className="call-log" data-testid="call-log">
      {calls.map((event) => {
        const data = event.data;
        const summary = data.summary as Record<string, unknown> | undefined;
        const summaryText = summary ? JSON.stringify(summary) : "";
        const latency = typeof data.latency_ms === "number" ? data.latency_ms : null;
        const cost = typeof data.cost_usd === "number" ? data.cost_usd : null;
        const model = typeof data.model === "string" ? data.model : "";
        const role = typeof data.role === "string" ? data.role : "";
        const schema = typeof data.schema === "string" ? data.schema : "";
        const errorCode =
          data.error && typeof data.error === "object" && "code" in data.error
            ? String(data.error.code)
            : null;
        return (
          <li key={event.event_id} className={`call-log-row call-log-${event.status}`}>
            <span className="call-log-time">{formatTime(event.ts)}</span>
            <span className="call-log-status">{event.status === "failed" ? "err" : "ok"}</span>
            <code className="call-log-model">{model}</code>
            <span className="call-log-schema">{role}·{schema}</span>
            {summaryText && <span className="call-log-summary">{summaryText}</span>}
            {errorCode && <span className="call-log-error">{errorCode}</span>}
            <span className="call-log-meta">
              {latency !== null ? `${latency}ms` : ""}
              {cost !== null ? ` · $${cost.toFixed(4)}` : ""}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
```

`web/src/components/ProgressView.tsx`:
```tsx
"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { getJob, streamJobEvents } from "@/lib/api";
import type { GenerationJob, JobEvent, JobStatus } from "@/lib/types";
import { CallLog } from "./CallLog";

const STAGE_ORDER = [
  "planner",
  "ideation",
  "selection",
  "generation",
  "code_review",
  "sandbox",
  "blind",
  "critic",
  "judge",
  "done",
];

const STAGE_LABELS: Record<string, string> = {
  planner: "기획",
  ideation: "발상",
  selection: "선별",
  generation: "생성",
  code_review: "코드 심사",
  sandbox: "샌드박스 검증",
  blind: "블라인드 합의",
  critic: "비평",
  judge: "집계",
  done: "완료",
};

/** 실시간 생성 진행 화면 — 단계 체크리스트 + LLM 호출 로그 (SSE). */
export function ProgressView({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<GenerationJob | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [status, setStatus] = useState<JobStatus>("queued");
  const [error, setError] = useState<string | null>(null);
  const [reconnectKey, setReconnectKey] = useState(0);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    getJob(jobId)
      .then((data) => {
        if (!cancelled) {
          setJob(data);
          setStatus(data.status);
          setEvents(data.events);
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : String(reason));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [jobId, reconnectKey]);

  useEffect(() => {
    if (status !== "queued" && status !== "running") {
      return;
    }
    const close = streamJobEvents(jobId, {
      onEvent: (event) => setEvents((current) => [...current, event]),
      onDone: (finalStatus) => setStatus(finalStatus),
      onError: (message) => setError(message),
    });
    return close;
  }, [jobId, status, reconnectKey]);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [events]);

  const stageStatus = (stage: string): "done" | "active" | "pending" | "failed" => {
    if (events.some((event) => event.type === "stage" && event.stage === stage && event.status === "failed")) {
      return "failed";
    }
    if (events.some((event) => event.type === "stage" && event.stage === stage && event.status === "done")) {
      return "done";
    }
    if (events.some((event) => event.type === "stage" && event.stage === stage && event.status === "started")) {
      return "active";
    }
    return "pending";
  };

  const handleRetry = () => {
    setError(null);
    setReconnectKey((key) => key + 1);
  };

  return (
    <div className="progress-view">
      {error && (
        <div className="progress-error" role="alert">
          <p>{error}</p>
          <button type="button" onClick={handleRetry}>
            다시 연결
          </button>
        </div>
      )}

      {status === "completed" && (
        <p className="progress-done">
          생성이 완료되었습니다.{" "}
          <Link href={`/runs/${jobId}/review`}>검토 화면으로 이동 →</Link>
        </p>
      )}

      <div className="progress-grid">
        <section className="progress-stages" aria-label="단계 체크리스트">
          <h2>작업 목록</h2>
          <ol className="stage-list">
            {STAGE_ORDER.map((stage) => {
              const state = stageStatus(stage);
              const candidateEvents = events.filter(
                (event) => event.type === "stage" && event.stage === stage,
              );
              return (
                <li key={stage} className={`stage-row stage-${state}`} data-testid={`stage-${stage}`}>
                  <span className="stage-marker">
                    {state === "done" ? "☑" : state === "failed" ? "✕" : state === "active" ? "◐" : "○"}
                  </span>
                  <span className="stage-label">{STAGE_LABELS[stage] ?? stage}</span>
                  {candidateEvents.length > 0 && (
                    <span className="stage-message">{candidateEvents.at(-1)?.message}</span>
                  )}
                </li>
              );
            })}
          </ol>
        </section>

        <section className="progress-log" ref={logRef} aria-label="LLM 호출 로그">
          <h2>LLM 호출 로그</h2>
          <CallLog events={events} />
        </section>
      </div>
    </div>
  );
}
```

`web/src/app/runs/[runId]/progress/ProgressClient.tsx`:
```tsx
"use client";

import { use } from "react";
import Link from "next/link";

import { ProgressView } from "@/components/ProgressView";

/** 진행 화면 클라이언트 — 동적 경로 파라미터를 해석해 ProgressView 에 전달한다. */
export function ProgressClient({ runIdPromise }: { runIdPromise: Promise<{ runId: string }> }) {
  const { runId } = use(runIdPromise);
  return (
    <>
      <header className="progress-header">
        <p className="progress-eyebrow">
          <Link className="progress-back" href="/">
            ← 실행 목록
          </Link>
        </p>
        <h1>생성 진행</h1>
        <p className="progress-sub">
          실행 <code>{runId}</code> · 실시간 진행 상황
        </p>
      </header>
      <ProgressView jobId={runId} />
    </>
  );
}
```

`web/src/app/runs/[runId]/progress/page.tsx`:
```tsx
import type { Metadata } from "next";

import { ProgressClient } from "./ProgressClient";

export const metadata: Metadata = {
  title: "생성 진행",
};

export default function RunProgressPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  return (
    <main className="progress-page">
      <div className="page-frame">
        <ProgressClient runIdPromise={params} />
      </div>
    </main>
  );
}
```
> Next.js 16 규칙 확인: 동적 라우트 `params`는 Promise. 기존 `review/page.tsx` 패턴 그대로 따른다.

**Step 4: 테스트 실행 (통과 확인)**

Run (workdir `web`): `npm run test`
Expected: PASS

**Step 5: 타입·린트**

Run (workdir `web`): `npm run typecheck; npm run lint`
Expected: 통과

**Step 6: 커밋**

```bash
git add web/src/app/runs/[runId]/progress web/src/components/ProgressView.tsx web/src/components/CallLog.tsx web/src/components/__tests__/ProgressView.test.tsx web/src/components/__tests__/CallLog.test.tsx
git commit -m "feat: add live progress view with LLM call log via SSE"
```

---

## Task 12: 문제 라이브러리 화면 + 홈 버튼

**Files:**
- Create: `web/src/app/problems/page.tsx`
- Create: `web/src/components/ProblemLibrary.tsx`
- Create: `web/src/components/__tests__/ProblemLibrary.test.tsx`
- Modify: `web/src/app/page.tsx` (홈에 "새 문제 만들기" 버튼 + 라이브러리 링크)

**Step 1: 실패 테스트 작성**

`web/src/components/__tests__/ProblemLibrary.test.tsx`:
```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProblemLibrary } from "../ProblemLibrary";
import * as api from "@/lib/api";

describe("ProblemLibrary (T08)", () => {
  it("문제를 목록으로 보여주고 삭제할 수 있다", async () => {
    vi.spyOn(api, "listProblems").mockResolvedValue([
      { problem_id: "p1", title: "광명북고 Q19", text: "포물선 문제", source: "manual", source_run_id: null, created_at: "" },
    ]);
    const del = vi.spyOn(api, "deleteProblem").mockResolvedValue();
    render(<ProblemLibrary />);
    await waitFor(() => expect(screen.getByText("광명북고 Q19")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /삭제/ }));
    await waitFor(() => expect(del).toHaveBeenCalledWith("p1"));
  });

  it("새 문제를 등록한다", async () => {
    vi.spyOn(api, "listProblems").mockResolvedValue([]);
    vi.spyOn(api, "registerProblem").mockResolvedValue({
      problem_id: "p2", title: "", text: "새 문제", source: "manual", source_run_id: null, created_at: "",
    });
    render(<ProblemLibrary />);
    await userEvent.type(screen.getByLabelText(/새 문제 텍스트/), "새 문제 본문");
    await userEvent.click(screen.getByRole("button", { name: /등록/ }));
    await waitFor(() =>
      expect(api.registerProblem).toHaveBeenCalledWith(expect.objectContaining({ text: "새 문제 본문" })),
    );
  });
});
```

**Step 2: 테스트 실행 (실패 확인)**

Run (workdir `web`): `npm run test`
Expected: FAIL — 컴포넌트 없음.

**Step 3: 구현**

`web/src/components/ProblemLibrary.tsx`:
```tsx
"use client";

import { useEffect, useState } from "react";

import { deleteProblem, listProblems, registerProblem } from "@/lib/api";
import type { Problem } from "@/lib/types";

/** 문제 라이브러리 관리 — 목록·등록·삭제. */
export function ProblemLibrary() {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    listProblems()
      .then(setProblems)
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : String(reason)),
      );
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleRegister = async () => {
    if (!text.trim()) {
      return;
    }
    try {
      await registerProblem({ text: text.trim(), title: title.trim() });
      setText("");
      setTitle("");
      refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  const handleDelete = async (problemId: string) => {
    try {
      await deleteProblem(problemId);
      refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  return (
    <div className="problem-library">
      {error && <p className="problems-error">{error}</p>}

      <section className="problems-register">
        <h2>새 문제 등록</h2>
        <input
          aria-label="새 문제 제목"
          placeholder="제목 (선택)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          aria-label="새 문제 텍스트"
          placeholder="문제 본문"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
        />
        <button type="button" className="button-register" onClick={handleRegister} disabled={!text.trim()}>
          등록
        </button>
      </section>

      <section className="problems-list">
        <h2>문제 목록</h2>
        {problems.length === 0 ? (
          <p className="problems-empty">등록된 문제가 없습니다.</p>
        ) : (
          <ul className="problem-rows">
            {problems.map((problem) => (
              <li key={problem.problem_id} className="problem-row" data-testid={`problem-${problem.problem_id}`}>
                <div className="problem-row-text">
                  <strong>{problem.title || problem.problem_id}</strong>
                  <p>{problem.text}</p>
                  <span className="problem-source">
                    {problem.source === "approved" ? "승인 문제" : "직접 등록"}
                    {problem.source_run_id ? ` (${problem.source_run_id})` : ""}
                  </span>
                </div>
                <button
                  type="button"
                  className="button-delete"
                  onClick={() => handleDelete(problem.problem_id)}
                >
                  삭제
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
```

`web/src/app/problems/page.tsx`:
```tsx
import type { Metadata } from "next";
import Link from "next/link";

import { ProblemLibrary } from "@/components/ProblemLibrary";

export const metadata: Metadata = {
  title: "문제 라이브러리",
};

export default function ProblemsPage() {
  return (
    <main className="problems-page">
      <div className="page-frame">
        <header className="problems-header">
          <p className="problems-eyebrow">
            <Link href="/">← 실행 목록</Link>
          </p>
          <h1>문제 라이브러리</h1>
          <p className="problems-sub">
            원문제를 등록하거나, 검토에서 승인된 문제를 확인할 수 있습니다.
          </p>
        </header>
        <ProblemLibrary />
      </div>
    </main>
  );
}
```

`web/src/app/page.tsx` — 홈 헤더 아래에 액션 버튼 추가:
```tsx
import Link from "next/link";
import { RunList } from "@/components/RunList";

export default function HomePage() {
  return (
    <main className="home-page">
      <header className="home-header">
        <p className="home-eyebrow">공통수학Ⅱ · 도형의 방정식</p>
        <h1>수학문제 변형·생성기</h1>
        <p className="home-sub">검증된 변형 후보를 교사가 검토하고 승인·반려하는 작업대</p>
        <div className="home-actions">
          <Link className="home-action-primary" href="/create">
            새 문제 만들기
          </Link>
          <Link className="home-action-secondary" href="/problems">
            문제 라이브러리
          </Link>
        </div>
      </header>
      <RunList />
    </main>
  );
}
```

**Step 4: 테스트 실행 (통과 확인)**

Run (workdir `web`): `npm run test`
Expected: PASS

**Step 5: 타입·린트**

Run (workdir `web`): `npm run typecheck; npm run lint`
Expected: 통과

**Step 6: 커밋**

```bash
git add web/src/app/problems web/src/components/ProblemLibrary.tsx web/src/components/__tests__/ProblemLibrary.test.tsx web/src/app/page.tsx
git commit -m "feat: add problem library page and home actions"
```

---

## Task 13: 스타일 (globals.css) + 통합 회귀 + TASKS_INDEX 갱신

**Files:**
- Modify: `web/src/app/globals.css`
- Modify: `tasks/TASKS_INDEX.md`

**Step 1: 스타일 추가**

`web/src/app/globals.css` 끝에 기존 테마(종이·잉크·진사색)를 따르는 스타일 추가:
- `.home-actions`, `.home-action-primary/secondary` (홈 버튼)
- `.create-page`, `.create-header`, `.create-form`, `.create-source`, `.create-options`, `.create-actions`, `.button-create`, `.create-error`
- `.problem-picker`, `.progress-page`, `.progress-header`, `.progress-grid`, `.progress-stages`, `.stage-list`, `.stage-row`, `.stage-marker`, `.progress-log`, `.call-log`, `.call-log-row`, `.call-log-ok/started/failed`, `.progress-done`, `.progress-error`
- `.problems-page`, `.problems-header`, `.problem-library`, `.problems-register`, `.problems-list`, `.problem-rows`, `.problem-row`, `.button-register`, `.button-delete`

> CSS 클래스는 각 Task의 JSX에서 사용한 것과 일치해야 한다. 시험지·교정본 분위기(종이 톤 + 잉크 + 진사 액센트)를 유지하고, 생성 중 활성 단계는 진사색, 완료는 세이지색, 실패는 적색으로 표시한다.

**Step 2: 통합 회귀 실행**

Run: `math-variant gate` (또는 아래 명령을 순차 실행)
```bash
.venv\Scripts\python -m ruff check src tests infra
.venv\Scripts\python -m ruff format --check src tests infra
.venv\Scripts\python -m mypy
.venv\Scripts\python -m pytest
cmd /c "cd web && npm run lint"
cmd /c "cd web && npm run typecheck"
cmd /c "cd web && npm run test"
```
Expected: 전부 통과 (pytest 154+α, vitest 기존 4건 + 신규)

**Step 3: TASKS_INDEX.md 갱신**

`tasks/TASKS_INDEX.md` 표에 T08 행 추가:
```markdown
| **T08.1** | [T08 웹 생성 워크플로 구현](../docs/plans/2026-08-12-web-generation-workflow.md) | P8 웹 생성 | 프론트엔드·API | P1 | 8 | ✅ | ✅ Done | 원문제→파이프라인 실행, 단계·LLM 호출 실시간 표시, 승인 문제 라이브러리 자동 보관 |
```

**Step 4: 수동 확인 지침 (README 또는 설계 문서 참고)**

- API: `.venv\Scripts\python -m uvicorn math_variant.api.app:app --port 8000`
- 웹: `cmd /c "cd web && npm run dev"`
- 브라우저 http://localhost:3000 에서 "새 문제 만들기" → 텍스트 붙여넣기 → 생성 시작 → 진행 화면(단계 + LLM 로그) → 완료 → 검토 화면
- 실제 LLM 실행은 유료이므로 사용자가 로컬에서 확인

**Step 5: 커밋**

```bash
git add web/src/app/globals.css tasks/TASKS_INDEX.md
git commit -m "style: add generation workflow styles and register T08 tasks"
```

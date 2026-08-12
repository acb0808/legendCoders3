"""진행·LLM 호출 이벤트 모델 (웹 생성 워크플로).

의존성 방향: providers/structured.py 와 agents/pipeline.py 가 공통으로 import 한다.
providers → api 로의 의존을 피하기 위해 최상위 모듈에 둔다. (설계 문서의 api/events.py
위치와 다르지만 레이어를 깨끗하게 유지한다.)
"""

from __future__ import annotations

from datetime import UTC, datetime
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
    "CodeReviewOutput": ("verdict",),
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

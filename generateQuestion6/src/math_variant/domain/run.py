"""GenerationRun — 전체 상태 머신·재시도·비용·지연·버전·사람 판단."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RunState(StrEnum):
    """권고 상태 머신 (문서 02 §4.2)."""

    INGESTED = "INGESTED"
    NORMALIZED = "NORMALIZED"
    ANALYZED = "ANALYZED"
    IR_COMPILED = "IR_COMPILED"
    IR_VERIFIED = "IR_VERIFIED"
    PLAN_APPROVED = "PLAN_APPROVED"
    CANDIDATES_GENERATED = "CANDIDATES_GENERATED"
    NOVELTY_VERIFIED = "NOVELTY_VERIFIED"
    TOOL_VERIFIED = "TOOL_VERIFIED"
    CROSS_SOLVED = "CROSS_SOLVED"
    ADVERSARIAL_VERIFIED = "ADVERSARIAL_VERIFIED"
    PEDAGOGY_VERIFIED = "PEDAGOGY_VERIFIED"
    DIFFICULTY_ESTIMATED = "DIFFICULTY_ESTIMATED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


STATE_ORDER: tuple[RunState, ...] = tuple(RunState.__members__.values())


class RunStage(BaseModel):
    """한 단계의 실행 기록."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state: RunState
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    attempts: int = 1
    error_code: str | None = None
    evidence_ref: str | None = None


class HumanDecision(BaseModel):
    """교사 승인·반려 결정."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision: str  # approved | rejected
    reject_reason_code: str | None = None
    reject_reason_detail: str | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decided_by: str


class GenerationRun(BaseModel):
    """전체 실행 상태 컨테이너."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    source_ref: str
    state: RunState = RunState.INGESTED
    stages: list[RunStage] = Field(default_factory=list)
    spec_id: str | None = None
    plan_ids: list[str] = Field(default_factory=list)
    candidate_ids: list[str] = Field(default_factory=list)
    human_decision: HumanDecision | None = None
    retry_budget: int = 2
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    version: str = "0.1.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def transition(self, target: RunState, *, error_code: str | None = None) -> None:
        """앞으로만 전이하는 상태 머신."""
        if self.state == RunState.REJECTED or self.state == RunState.FAILED:
            raise ValueError(f"종료 상태({self.state})에서 전이할 수 없다")
        current_index = STATE_ORDER.index(self.state)
        target_index = STATE_ORDER.index(target)
        if target_index < current_index:
            raise ValueError(f"상태 되돌림 금지: {self.state} -> {target}")
        self.stages.append(RunStage(state=target, error_code=error_code))
        self.state = target
        self.updated_at = datetime.now(UTC)

    def gate_transition(self, target: RunState, evidence_ok: bool) -> None:
        """결정론적 게이트를 통과해야만 다음 상태로 전이한다."""
        if not evidence_ok:
            raise ValueError(f"증거 없이 {target} 로 전이할 수 없다 (fail-closed)")
        self.transition(target)

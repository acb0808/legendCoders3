"""구조화된 오류 코드와 감사 가능한 실패 표현.

원칙: 모든 실패·판단 불능 상태는 자유 문장이 아니라 코드로 남는다.
새 실패 상태를 추가할 때는 반드시 여기에 코드를 등록하고, 왜 실패했는지 판단할 수 있는
context를 함께 채운다.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(StrEnum):
    """파이프라인 전 구간에서 사용하는 실패·판단 불능 코드."""

    # --- P0 기반 ---
    DEPENDENCY_LOCK_MISSING = "DEPENDENCY_LOCK_MISSING"

    # --- P1 도메인·저장 ---
    PLAN_CHANGE_DIMENSION_SHORTAGE = "PLAN_CHANGE_DIMENSION_SHORTAGE"
    PLAN_STRUCTURAL_CHANGE_SHORTAGE = "PLAN_STRUCTURAL_CHANGE_SHORTAGE"
    PLAN_DRIFT = "PLAN_DRIFT"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"
    RULE_CONFLICT = "RULE_CONFLICT"
    UNSUPPORTED_CONCEPT = "UNSUPPORTED_CONCEPT"

    # --- P2 원문 분석 ---
    AMBIGUOUS_OR_MULTI_SOLUTION = "AMBIGUOUS_OR_MULTI_SOLUTION"
    UNSATISFIABLE_SOURCE = "UNSATISFIABLE_SOURCE"
    SOURCE_UNRESOLVED = "SOURCE_UNRESOLVED"
    SOURCE_ANSWER_MISMATCH = "SOURCE_ANSWER_MISMATCH"
    PARSE_REJECTED = "PARSE_REJECTED"

    # --- P3 샌드박스 ---
    SANDBOX_POLICY_VIOLATION = "SANDBOX_POLICY_VIOLATION"
    SANDBOX_TIMEOUT = "SANDBOX_TIMEOUT"
    SANDBOX_CODE_ERROR = "SANDBOX_CODE_ERROR"
    SANDBOX_INFRA_ERROR = "SANDBOX_INFRA_ERROR"

    # --- P4 변형 계획 ---
    SURFACE_BLACKLIST = "SURFACE_BLACKLIST"

    # --- P5 검증·루브릭 ---
    SOLVER_DISAGREEMENT = "SOLVER_DISAGREEMENT"
    FORBIDDEN_INFO_LEAK = "FORBIDDEN_INFO_LEAK"
    NOVELTY_FAILURE = "NOVELTY_FAILURE"
    AMBIGUITY_FLAG = "AMBIGUITY_FLAG"

    # --- T07 다중 에이전트 ---
    AGENT_UNRESOLVED = "AGENT_UNRESOLVED"
    SCRIPT_REVIEW_REJECTED = "SCRIPT_REVIEW_REJECTED"


class StructuredError(BaseModel):
    """감사 로그와 API 응답에 그대로 실을 수 있는 실패 레코드."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: ErrorCode
    message: str
    context: dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover - 표현 편의
        return f"[{self.code}] {self.message}"


class MathVariantError(Exception):
    """구조화된 오류를 그대로 전달하는 애플리케이션 예외."""

    def __init__(self, error: StructuredError) -> None:
        super().__init__(str(error))
        self.error = error

    @property
    def code(self) -> ErrorCode:
        return self.error.code

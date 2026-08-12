"""CandidateProblem — 문제 본문·기계 형식화·주장 답·풀이·변형 근거.

검증 전 후보의 답과 해설은 주장(claim)일 뿐이며 PASS 상태를 자동으로 부여하지 않는다.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

VerificationStatus = Literal["UNVERIFIED", "PASS", "FAIL", "UNRESOLVED"]


class Formalization(BaseModel):
    """후보의 기계 형식화 — 계획의 symbols·constraints·goal 과 비교된다."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbols: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    goal: str
    domain: str | None = None


class SolutionStepClaim(BaseModel):
    """생성기가 주장하는 풀이 단계 (검증 전)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_id: str
    statement: str
    justification: str = Field(default="")
    claimed: bool = True


class CandidateProblem(BaseModel):
    """승인된 계획 하나에서 생성된 문제 후보."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    plan_id: str
    problem_text: str = Field(min_length=1)
    formalization: Formalization
    final_answer_claim: str
    solution_steps: list[SolutionStepClaim] = Field(default_factory=list)
    transformation_evidence: list[dict[str, Any]] = Field(default_factory=list)
    verification_status: VerificationStatus = "UNVERIFIED"
    validation_ref: str | None = None

    def mark_verified(self, status: VerificationStatus, validation_ref: str) -> None:
        """검증 결과를 반영한다. 주장 답만으로는 호출할 수 없다."""
        self.verification_status = status
        self.validation_ref = validation_ref

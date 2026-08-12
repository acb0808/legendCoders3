"""Source Gate — 원문이 변형 계획 단계로 진입해도 되는지 판정한다 (T02.5).

PASS 일 때만 다음 단계로 전이한다. 잘못된 원문(모순·조건 부족·답 불일치·판단 불능)은
모두 차단한다.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from math_variant.domain.problem import ProblemSpec
from math_variant.services.baseline_solver import BaselineSolution


class SourceGateStatus(StrEnum):
    PASS = "PASS"  # noqa: S105 - 게이트 상태 코드 (비밀 아님)
    AMBIGUOUS_OR_MULTI_SOLUTION = "AMBIGUOUS_OR_MULTI_SOLUTION"
    UNSATISFIABLE_SOURCE = "UNSATISFIABLE_SOURCE"
    SOURCE_UNRESOLVED = "SOURCE_UNRESOLVED"
    SOURCE_ANSWER_MISMATCH = "SOURCE_ANSWER_MISMATCH"


class SourceGateResult(BaseModel):
    """게이트 판정 결과."""

    model_config = ConfigDict(extra="forbid")

    status: SourceGateStatus
    reason: str = ""
    answer_equivalence: str | None = None

    @property
    def passes(self) -> bool:
        return self.status == SourceGateStatus.PASS


class SourceGate:
    """원문 게이트: PASS 일 때만 계획 단계로 전이를 허용한다."""

    def evaluate(
        self,
        spec: ProblemSpec,
        baseline: BaselineSolution,
        provided_answer: str | None = None,
    ) -> SourceGateResult:
        if spec.has_unresolved_assumptions or baseline.status == "UNRESOLVED":
            return SourceGateResult(
                status=SourceGateStatus.SOURCE_UNRESOLVED,
                reason=baseline.reason or "원문 판단 불가 (fail-closed)",
            )
        if baseline.status == "UNSATISFIABLE":
            return SourceGateResult(
                status=SourceGateStatus.UNSATISFIABLE_SOURCE,
                reason=baseline.reason,
            )
        if baseline.status == "AMBIGUOUS_OR_MULTI_SOLUTION":
            return SourceGateResult(
                status=SourceGateStatus.AMBIGUOUS_OR_MULTI_SOLUTION,
                reason=baseline.reason,
            )

        if provided_answer is not None and provided_answer.strip():
            equivalence = self._answers_equivalent(baseline.answer_set, [provided_answer])
            if not equivalence:
                return SourceGateResult(
                    status=SourceGateStatus.SOURCE_ANSWER_MISMATCH,
                    reason=(
                        "원문 제공 답과 독립 풀이가 다르다: "
                        f"제공={provided_answer!r}, 독립={baseline.answer_set!r}"
                    ),
                    answer_equivalence="mismatch",
                )

        return SourceGateResult(
            status=SourceGateStatus.PASS,
            answer_equivalence="match" if provided_answer else "no_provided_answer",
        )

    @staticmethod
    def _answers_equivalent(answer_set: list[str], provided: list[str]) -> bool:
        """주장 답 집합과 제공 답을 정규화된 형태로 비교한다."""
        if not answer_set:
            return False
        if len(provided) == 1 and len(answer_set) > 1:
            # "또는" 으로 묶인 답 문자열
            parts = [p.strip() for p in provided[0].replace("또는", "|").split("|") if p.strip()]
            return _normalize_set(answer_set) == _normalize_set(parts)
        return _normalize_set(answer_set) == _normalize_set(provided)


def _normalize_set(items: list[str]) -> set[str]:
    cleaned: set[str] = set()
    for item in items:
        s = item.replace(" ", "").replace("=", "").replace("^", "**")
        cleaned.add(s)
    return cleaned

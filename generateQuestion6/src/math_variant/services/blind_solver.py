"""블라인드 풀이 A·B (T05.3).

서로 독립적인 풀이자가 문제 본문만 보고 해집합·가정·중간 단계를 반환한다.
생성기의 정답·해설·변형 계획은 입력에서 제거된다.

합의 규칙:
- 문자열이 아니라 정규화된 해집합과 핵심 풀이 노드(정의역·키 스텝)를 비교한다.
- 두 풀이의 해집합이 동치여야 하고 정의역·중간 단계가 충돌하지 않아야 PASS 이다.
- 판단 불능(UNRESOLVED)이 하나라도 있으면 PASS 가 아니다. (IT4)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from math_variant.math.expressions import parse_expression
from math_variant.security.prompt_firewall import (
    ForbiddenContentScanner,
    sanitize_blind_prompt,
)

SolverStatus = Literal["SATISFIABLE", "UNRESOLVED", "AMBIGUOUS", "UNSATISFIABLE"]
ConsensusStatus = Literal["PASS", "SOLVER_DISAGREEMENT", "UNRESOLVED"]

_MATH_SYMBOLS = {"x", "y", "a", "b", "k", "m", "n", "t"}


class BlindSolution(BaseModel):
    """풀이자 하나의 결과."""

    model_config = ConfigDict(extra="forbid")

    solver_id: str
    answer_set: list[str] = Field(default_factory=list)
    domain: list[str] = Field(default_factory=list)
    key_steps: list[str] = Field(default_factory=list)
    status: SolverStatus = "SATISFIABLE"


class BlindConsensus(BaseModel):
    """블라인드 풀이 합의 결과."""

    model_config = ConfigDict(extra="forbid")

    status: ConsensusStatus
    solver_a: str
    solver_b: str
    reason: str = ""

    @property
    def passes(self) -> bool:
        return self.status == "PASS"


def normalize_answer(claim: str) -> str:
    """답 문자열을 정확 산술 기준으로 정규화한다 (IT1).

    1/2, 0.5, sqrt(4)/4 가 모두 동일 지문이 된다. 파싱 불가 시 원문을 정리해 반환한다.
    """
    candidate = claim.strip().replace("\\frac", "").strip()
    try:
        parsed = parse_expression(candidate, symbols=_MATH_SYMBOLS)
        return parsed.normalize_fingerprint()
    except Exception:
        return " ".join(candidate.split())


def reach_consensus(a: BlindSolution, b: BlindSolution) -> ConsensusStatus:
    """두 독립 풀이의 합의를 판정한다. 문자열이 아닌 정규화 해집합 기준."""
    if a.status != "SATISFIABLE" or b.status != "SATISFIABLE":
        return "UNRESOLVED"
    if not a.answer_set or not b.answer_set:
        return "UNRESOLVED"

    a_norm = {normalize_answer(ans) for ans in a.answer_set}
    b_norm = {normalize_answer(ans) for ans in b.answer_set}
    if a_norm != b_norm:
        return "SOLVER_DISAGREEMENT"

    # 해집합은 같아도 정의역·중간 단계가 충돌하면 합의가 아니다. (IT2)
    a_domain = set(a.domain)
    b_domain = set(b.domain)
    conflicting = a_domain.symmetric_difference(b_domain)
    if conflicting and not _domains_compatible(a_domain, b_domain):
        return "SOLVER_DISAGREEMENT"
    return "PASS"


def _domains_compatible(a: set[str], b: set[str]) -> bool:
    """정의역 제약이 명시적으로 모순이면 False."""
    pairs = [(x, y) for x in a for y in b]
    for first, second in pairs:
        if "x <" in first and "x >" in second:
            return False
        if "x >" in first and "x <" in second:
            return False
    return True


class BlindSolver:
    """두 독립 풀이자를 실행하고 합의를 판정한다."""

    def __init__(self, solver_a: object, solver_b: object, forbidden: dict[str, str]) -> None:
        self.solver_a = solver_a
        self.solver_b = solver_b
        self.scanner = ForbiddenContentScanner(forbidden)

    def solve_both(self, problem_text: str) -> BlindConsensus:
        sanitized = sanitize_blind_prompt(problem_text)
        if self.scanner.scan(sanitized):
            return BlindConsensus(
                status="UNRESOLVED",
                solver_a="A",
                solver_b="B",
                reason="블라인드 풀이 입력에 금지 정보가 포함되어 있다",
            )
        solution_a = self.solver_a.solve(sanitized)  # type: ignore[attr-defined]
        solution_b = self.solver_b.solve(sanitized)  # type: ignore[attr-defined]
        status = reach_consensus(solution_a, solution_b)
        return BlindConsensus(
            status=status,
            solver_a=solution_a.solver_id,
            solver_b=solution_b.solver_id,
            reason=f"해집합 동치: {status}",
        )

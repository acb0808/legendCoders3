"""T05.3 — 답 동치 통합 테스트 (정규화된 해집합·핵심 단계 비교)."""

from __future__ import annotations

from math_variant.domain.validation import CheckResult, ValidationEvidence, overall_status
from math_variant.services.blind_solver import BlindSolution, BlindSolver, reach_consensus

_FORBIDDEN = {"원문 정답": "", "해설": "", "변형 계획": "", "생성기 주장 답": ""}


class StaticSolver:
    def __init__(self, solution: BlindSolution) -> None:
        self.solution = solution

    def solve(self, problem_text: str) -> BlindSolution:
        return self.solution


def _sol(solver_id: str, answers: list[str], **kw: object) -> BlindSolution:
    base: dict = {
        "solver_id": solver_id,
        "answer_set": answers,
        "domain": [],
        "key_steps": [],
        "status": "SATISFIABLE",
    }
    base.update(kw)
    return BlindSolution(**base)


def _evidence(status: str) -> ValidationEvidence:
    return ValidationEvidence(
        checks=[
            CheckResult(
                check_id=f"blind-{status}",
                kind="blind",
                status=status,  # type: ignore[arg-type]
                critical=True,
            )
        ]
    )


def test_it1_1over2_point5_sqrt4over4_agree() -> None:
    a = _sol("A", ["1/2"])
    b = _sol("B", ["0.5"])
    c = _sol("C", ["sqrt(4)/4"])

    assert reach_consensus(a, b) == "PASS"
    assert reach_consensus(b, c) == "PASS"


def test_it2_domain_conflict_is_not_agreement() -> None:
    a = _sol("A", ["1/2"], domain=["x > 0"])
    b = _sol("B", ["0.5"], domain=["x < 0"])

    assert reach_consensus(a, b) == "SOLVER_DISAGREEMENT"
    # 합의가 아니므로 전체 검증 증거도 PASS 가 아니다.
    evidence = _evidence("PASS")
    evidence.checks.append(
        CheckResult(check_id="blind-disagree", kind="blind", status="FAIL", critical=True)
    )
    assert overall_status(evidence.checks) == "FAIL"


def test_it3_disagreement_not_auto_approved() -> None:
    a = _sol("A", ["x = 2"])
    b = _sol("B", ["x = -2"])

    consensus = BlindSolver(StaticSolver(a), StaticSolver(b), _FORBIDDEN).solve_both("문제")
    assert consensus.status == "SOLVER_DISAGREEMENT"
    assert consensus.passes is False


def test_it4_one_solver_failure_does_not_pass() -> None:
    ok = _sol("A", ["1/2"])
    unresolved = _sol("B", [], status="UNRESOLVED")

    consensus = BlindSolver(StaticSolver(ok), StaticSolver(unresolved), _FORBIDDEN).solve_both(
        "문제"
    )
    assert consensus.status == "UNRESOLVED"
    assert consensus.passes is False

"""T05.3 — 블라인드 풀이 A·B와 정보 누출 차단 테스트.

- T05.3-CT1: 캡처된 모든 풀이 요청에 금지 필드가 0개다.
- T05.3-IT1: 1/2, 0.5, sqrt(4)/4 답이 동치로 합의된다.
- T05.3-IT2: 같은 최종 답이지만 정의역·중간 단계가 충돌하면 합의로 처리하지 않는다.
- T05.3-IT3: 두 풀이가 다르면 SOLVER_DISAGREEMENT이고 자동 승인되지 않는다.
- T05.3-IT4: 공급자 하나가 실패해도 다른 풀이만으로 PASS하지 않는다.
"""

from __future__ import annotations

from math_variant.security.prompt_firewall import (
    ForbiddenContentScanner,
    sanitize_blind_prompt,
)
from math_variant.services.blind_solver import (
    BlindSolution,
    BlindSolver,
    normalize_answer,
    reach_consensus,
)

_FORBIDDEN = {
    "원문 정답": "x = 2",
    "해설": "거리 조건을 이용해 푼다",
    "변형 계획": "plan-1",
    "생성기 주장 답": "3x + 4y = 25",
}


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


def test_ct1_captured_solver_requests_have_zero_forbidden_fields() -> None:
    captured: list[dict] = []

    class CapturingSolver:
        def solve(self, problem_text: str) -> BlindSolution:
            captured.append({"problem_text": problem_text})
            return _sol("A", ["1/2"])

    solver = BlindSolver(CapturingSolver(), CapturingSolver(), _FORBIDDEN)
    solver.solve_both("문제 본문만")

    for request in captured:
        joined = " ".join(request.values())
        for field, value in _FORBIDDEN.items():
            assert field not in joined
            assert value not in joined


def test_it1_equivalent_answers_agree() -> None:
    a = _sol("A", ["1/2"])
    b = _sol("B", ["0.5"])
    c = _sol("C", ["sqrt(4)/4"])

    assert normalize_answer(a.answer_set[0]) == normalize_answer(b.answer_set[0])
    assert normalize_answer(a.answer_set[0]) == normalize_answer(c.answer_set[0])
    assert reach_consensus(a, b) == "PASS"
    assert reach_consensus(a, c) == "PASS"


def test_it2_same_answer_but_domain_conflict_not_consensus() -> None:
    a = _sol("A", ["1/2"], domain=["x > 0"])
    b = _sol("B", ["0.5"], domain=["x < 0"])

    assert reach_consensus(a, b) != "PASS"


def test_it3_different_answers_are_disagreement() -> None:
    a = _sol("A", ["x = 2"])
    b = _sol("B", ["x = -2"])

    assert reach_consensus(a, b) == "SOLVER_DISAGREEMENT"


def test_it4_single_solver_success_does_not_pass() -> None:
    a = _sol("A", ["1/2"])
    b = _sol("B", [], status="UNRESOLVED")

    assert reach_consensus(a, b) != "PASS"


def test_scanner_flags_forbidden_content() -> None:
    scanner = ForbiddenContentScanner(_FORBIDDEN)
    assert scanner.scan("생성기 주장 답 3x + 4y = 25 을 보고 풀라") is True
    assert scanner.scan("문제만 보고 풀라") is False


def test_sanitize_blind_prompt_removes_answer_tail() -> None:
    text = "접선의 방정식을 구하시오. 답: y = x + 100"
    sanitized = sanitize_blind_prompt(text)
    assert "y = x + 100" not in sanitized

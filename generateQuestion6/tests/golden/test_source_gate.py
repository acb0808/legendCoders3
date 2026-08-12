"""T02.5 — 원문 독립 풀이와 Source Gate 골드 테스트.

- T02.5-GT1: 정상 접선 문항은 검증된 해와 SolutionGraph를 반환한다.
- T02.5-GT2: 조건 하나가 빠진 다중 해 문항은 AMBIGUOUS_OR_MULTI_SOLUTION이다.
- T02.5-GT3: 모순 조건 문항은 UNSATISFIABLE_SOURCE다.
- T02.5-GT4: 원문 제공 답과 독립 풀이가 다르면 생성이 중단된다.
- T02.5-GT5: UNRESOLVED 원문이 계획 단계로 전이하지 못한다.
"""

from __future__ import annotations

import pytest

from math_variant.domain.problem import MathStatement, ProblemSpec
from math_variant.domain.scope import ScopeProfile
from math_variant.services.baseline_solver import BaselineSolver
from math_variant.verifiers.source_gate import SourceGate, SourceGateStatus


def _spec(
    text: str,
    *,
    provided_answer: str | None = None,
    unresolved: list[str] | None = None,
) -> ProblemSpec:
    return ProblemSpec(
        spec_id="s",
        source_text=text,
        curriculum_version="2022 개정",
        exam_scope=["도형의 방정식"],
        core_concepts=["원", "접선"],
        givens=[MathStatement(id="g", natural_language=text)],
        objective=MathStatement(id="goal", natural_language=text[:40]),
        answer_type="expression",
        explicit_assumptions=[],
        implicit_domain=[],
        expected_methods=[],
        unresolved_assumptions=unresolved or [],
    )


SCOPE = ScopeProfile(
    profile_id="p1",
    school_name="골드",
    exam_scope=["도형의 방정식"],
    allowed_units=["원의 방정식"],
    concept_vocabulary=["원", "직선", "접선", "좌표", "교점"],
    allowed_answer_types=["expression", "interval"],
)


def _run(text: str, provided_answer: str | None = None) -> tuple[object, SourceGateStatus]:
    spec = _spec(text, provided_answer=provided_answer)
    baseline = BaselineSolver(SCOPE).solve(spec)
    gate = SourceGate()
    result = gate.evaluate(spec, baseline, provided_answer)
    return baseline, result.status


def test_gt1_valid_tangent_returns_verified_solution() -> None:
    text = "점 (-6, 2)에서 원 x^2 + y^2 = 8에 그은 접선의 방정식을 구하시오."
    baseline, status = _run(text)

    assert status == SourceGateStatus.PASS
    assert baseline.status == "SATISFIABLE"
    assert baseline.graph.nodes, "SolutionGraph 에 검증된 노드가 있어야 한다"
    assert len(baseline.answer_set) == 2
    # 모든 접선 후보가 중심-직선 거리 = 반지름 조건을 통과했는지 검증 증거로 확인
    assert all(check.status == "PASS" for check in baseline.verification_checks), (
        baseline.verification_checks
    )


def test_gt2_missing_condition_is_ambiguous() -> None:
    # 접점/외부 점이 없으면 접선이 무한히 많다 → 조건 부족
    text = "원 x^2 + y^2 = 8의 접선의 방정식을 구하시오."
    _, status = _run(text)

    assert status == SourceGateStatus.AMBIGUOUS_OR_MULTI_SOLUTION


def test_gt3_contradictory_condition_is_unsatisfiable() -> None:
    # 반지름 제곱이 음수 → 원 자체가 존재할 수 없다
    text = "원 x^2 + y^2 = -4 위의 점에서 그은 접선의 방정식을 구하시오."
    _, status = _run(text)

    assert status == SourceGateStatus.UNSATISFIABLE_SOURCE


def test_gt4_provided_answer_mismatch_blocks_generation() -> None:
    text = "점 (-6, 2)에서 원 x^2 + y^2 = 8에 그은 접선의 방정식을 구하시오."
    baseline, status = _run(text, provided_answer="y = x + 100")

    assert status == SourceGateStatus.SOURCE_ANSWER_MISMATCH
    assert baseline.answer_set != ["y = x + 100"]


def test_gt5_unresolved_source_cannot_transition_to_plan() -> None:
    from math_variant.domain.run import GenerationRun, RunState

    text = "그래프가 다음 그림과 같은 함수의 식을 구하시오."  # 지원 외 도메인
    _baseline, status = _run(text)

    assert status == SourceGateStatus.SOURCE_UNRESOLVED

    run = GenerationRun(run_id="r", source_ref="s")
    run.transition(RunState.IR_VERIFIED)
    with pytest.raises(ValueError, match="fail-closed"):
        run.gate_transition(RunState.PLAN_APPROVED, evidence_ok=status == SourceGateStatus.PASS)

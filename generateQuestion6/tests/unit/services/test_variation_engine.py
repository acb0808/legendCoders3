"""T04.6 — 변형 엔진 구조적 변형 테스트.

목적: 변형이 숫자 치환·실생활 껍데기·기계적 절차가 아니라 "수학적 상황" 자체를
바꾸고, 그 내용이 transformation_evidence 에 정직하게 기록되는지 검증한다.
"""

from __future__ import annotations

from math_variant.domain.problem import MathStatement, ProblemSpec
from math_variant.domain.scope import ScopeProfile
from math_variant.domain.transformation import Dimension, TransformationPlan
from math_variant.services.baseline_solver import BaselineSolver
from math_variant.services.candidate_generator import validate_candidate_against_plan
from math_variant.services.geometry_parser import DeterministicSourceAnalyzer
from math_variant.services.variation_engine import VariationEngine
from math_variant.verifiers.source_gate import SourceGate

_SCOPE = ScopeProfile(
    profile_id="p1",
    school_name="테스트",
    exam_scope=["도형의 방정식"],
    allowed_units=["좌표와 직선", "원의 방정식", "도형의 이동"],
    concept_vocabulary=[
        "좌표",
        "직선",
        "원",
        "접선",
        "평행이동",
        "대칭이동",
        "교점",
        "거리",
        "중점",
        "방정식",
    ],
    allowed_answer_types=["expression", "interval", "coordinate"],
)

_PLAN = TransformationPlan(
    plan_id="plan-demo",
    preserved_concepts=["원", "직선의 위치 관계"],
    changed_dimensions=[
        Dimension.OBJECTIVE,
        Dimension.CONDITION_TOPOLOGY,
        Dimension.SOLUTION_ROUTE,
        Dimension.DATA_DOMAIN,
    ],
    change_description=[
        "접선 방정식 → k의 범위 (질문 역전)",
        "접점 1개 → 교점 2개 상황",
        "거리 → 판별식 경로",
        "값 변경",
    ],
    rule_ids=["RULE_OBJECTIVE_INVERSION", "RULE_CONDITION_TOPOLOGY", "RULE_TANGENT_DISCRIMINANT"],
    construction_blueprint="원-직선 위치 관계를 접선에서 할선 상황으로 재구성",
)

_SOURCE = "점 (-6, 2)에서 원 x^2 + y^2 = 8에 그은 접선의 방정식을 구하고, 그 풀이과정을 서술하시오."


def _spec():
    return DeterministicSourceAnalyzer(_SCOPE).analyze(_SOURCE)


def _variants():
    return VariationEngine(_SCOPE).generate_variants(_spec(), _PLAN)


def test_v1_tangent_situation_changed_to_secant() -> None:
    v1 = _variants()[0]

    # 상황이 접선(접점 1개) → 두 점에서 만나는 할선으로 바뀌었고, 문제에 "접선"이 아예 없다.
    assert "두 점에서 만나" in v1.problem_text
    assert "접선" not in v1.problem_text


def test_v1_objective_inverted_to_range() -> None:
    v1 = _variants()[0]

    assert "k의 범위" in v1.problem_text
    assert v1.final_answer_claim == "-5 < k < 5"


def test_v1_solution_uses_discriminant_route() -> None:
    v1 = _variants()[0]

    joined = " ".join(step.statement for step in v1.solution_steps)
    assert "판별식" in joined and "D > 0" in joined


def test_v2_finds_center_by_walking_inside() -> None:
    v2 = _variants()[1]

    assert "원 내부의 점" in v2.problem_text
    assert v2.final_answer_claim == "1"


def test_variations_are_not_pure_numeric_swaps() -> None:
    v1, v2 = _variants()

    # 원문의 데이터·목표가 그대로 남아 있으면 안 된다.
    for candidate in (v1, v2):
        assert "(-6" not in candidate.problem_text
        assert "x^2 + y^2 = 8" not in candidate.problem_text
    # 구조적 차원이 정직하게 기록된다.
    dimensions = {e["dimension"] for e in v1.transformation_evidence}
    assert {"objective", "condition_topology", "solution_route"} <= dimensions


def test_variations_stay_faithful_to_plan() -> None:
    spec = _spec()
    for candidate in _variants():
        failures = validate_candidate_against_plan(candidate, _PLAN, spec)
        assert failures == []


def test_v1_secant_variation_passes_fixed_verification() -> None:
    v1 = _variants()[0]

    new_baseline = BaselineSolver(_SCOPE).solve_text(v1.problem_text)
    gate = SourceGate().evaluate(_bare_spec(v1.problem_text), new_baseline)

    assert gate.passes is True, gate.reason
    assert new_baseline.answer_set == ["-5 < k < 5"]


def test_v2_center_walk_variation_passes_fixed_verification() -> None:
    v2 = _variants()[1]

    new_baseline = BaselineSolver(_SCOPE).solve_text(v2.problem_text)
    gate = SourceGate().evaluate(_bare_spec(v2.problem_text), new_baseline)

    assert gate.passes is True, gate.reason
    assert new_baseline.answer_set == ["1"]


def _bare_spec(text: str) -> ProblemSpec:
    return ProblemSpec(
        spec_id="verify",
        source_text=text,
        curriculum_version="2022 개정",
        exam_scope=["도형의 방정식"],
        core_concepts=["원"],
        objective=MathStatement(id="goal", natural_language="문제 본문"),
        answer_type="expression",
        unresolved_assumptions=[],
    )

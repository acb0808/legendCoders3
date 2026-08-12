"""T04.1 — 도형의 방정식 변형 규칙 카탈로그 테스트.

- T04.1-UT1: 원이 없는 ProblemSpec 에는 circle 변형 규칙이 적용되지 않는다.
- T04.1-UT2: 접선 규칙은 반지름과 직선 또는 동치 구성을 요구한다.
- T04.1-UT3: 상충 규칙 조합은 RULE_CONFLICT 로 거부된다.
- T04.1-UT4: 각 규칙은 최소 하나의 실행 가능한 verifier_recipe 를 가진다.
- T04.1-UT5: 규칙 카탈로그의 모든 개념 ID 가 ScopeProfile 어휘에 존재한다.
"""

from __future__ import annotations

from math_variant.domain.problem import MathStatement, ProblemSpec
from math_variant.domain.scope import ScopeProfile
from math_variant.errors import MathVariantError
from math_variant.rules.geometry import build_geometry_catalog

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


def _spec(core: list[str]) -> ProblemSpec:
    return ProblemSpec(
        spec_id="s",
        source_text="원과 접선 문제",
        curriculum_version="2022 개정",
        exam_scope=["도형의 방정식"],
        core_concepts=core,
        objective=MathStatement(id="goal", natural_language="접선의 방정식을 구하시오"),
        answer_type="expression",
    )


def test_ut1_circle_rule_not_applied_without_circle() -> None:
    catalog = build_geometry_catalog(_SCOPE)
    spec = _spec(["직선"])

    applicable = catalog.rules_for(spec)
    assert all(rule.rule_id != "RULE_CIRCLE_CENTER_RADIUS" for rule in applicable)


def test_ut2_tangent_rule_requires_radius_and_line() -> None:
    catalog = build_geometry_catalog(_SCOPE)
    rule = catalog.get("RULE_TANGENT_DISTANCE")

    assert rule.applies_to(_spec(["원", "직선", "접선"])) is True
    # 반지름/직선 없이는 적용할 수 없다 (전제 부족 → 적용 불가)
    assert rule.applies_to(_spec(["원"])) is False


def test_ut3_conflicting_rules_rejected() -> None:
    catalog = build_geometry_catalog(_SCOPE)
    rules = ["RULE_CIRCLE_CENTER_RADIUS", "RULE_CIRCLE_GENERAL_FORM"]

    try:
        catalog.validate_combination(rules)
    except MathVariantError as exc:
        assert exc.code == "RULE_CONFLICT"
    else:  # pragma: no cover
        raise AssertionError("상충 규칙 조합이 RULE_CONFLICT 로 거부되지 않았다")


def test_ut4_every_rule_has_executable_verifier_recipe() -> None:
    catalog = build_geometry_catalog(_SCOPE)

    for rule in catalog.all_rules():
        assert rule.verifier_recipe, f"{rule.rule_id} 에 verifier_recipe 가 없다"
        assert any(
            item.startswith("sympy") or item.startswith("numeric") for item in rule.verifier_recipe
        ), f"{rule.rule_id} 에 실행 가능한 검증 레시피가 없다"


def test_ut5_rule_concepts_exist_in_scope_vocabulary() -> None:
    catalog = build_geometry_catalog(_SCOPE)

    for rule in catalog.all_rules():
        for concept in rule.concepts:
            assert concept in _SCOPE.concept_vocabulary, (
                f"{rule.rule_id} 의 개념 {concept} 이 ScopeProfile 어휘에 없다"
            )

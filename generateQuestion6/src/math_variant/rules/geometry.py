"""도형의 방정식 변형 규칙 카탈로그 (T04.1).

지원 규칙:
- 직선 직접식 ↔ 두 점·기울기·교점
- 원 직접식 ↔ 중심·반지름·자취
- 접선 ↔ 거리·판별식
- 질문 역전, 조건 위상, 변수 역할, 보조 구성, 이동·대칭
"""

from __future__ import annotations

from math_variant.domain.scope import ScopeProfile
from math_variant.domain.transformation import Dimension
from math_variant.rules.base import RuleCatalog, RuleDefinition


def build_geometry_catalog(scope: ScopeProfile) -> RuleCatalog:
    """ScopeProfile 의 허용 개념 어휘에 맞춘 규칙 카탈로그를 만든다."""
    _ = scope
    return RuleCatalog(_RULES)


_LINE = Dimension.CONDITION_TOPOLOGY
_OBJ = Dimension.OBJECTIVE
_CTX = Dimension.CONTEXT
_REP = Dimension.REPRESENTATION
_DATA = Dimension.DATA_DOMAIN
_ORDER = Dimension.CONDITION_ORDER
_AUX = Dimension.AUXILIARY_CONSTRUCTION
_ROUTE = Dimension.SOLUTION_ROUTE

_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="RULE_LINE_TWO_POINTS",
        name="직선을 두 점으로 표현",
        description="직선의 방정식을 두 점·기울기·교점 구성으로 재표현한다.",
        concepts=["직선", "좌표"],
        preconditions=["직선"],
        changed_dimensions=[_REP, _CTX, _DATA],
        construction_template=(
            "직선 ax + by + c = 0 을 두 점 (x1,y1),(x2,y2) 또는 기울기와 한 점으로 제시한다."
        ),
        difficulty_delta=0.2,
        verifier_recipe=[
            "sympy: 두 점이 원래 직선 위에 있는지 검증",
            "sympy: 직선 방정식 동치 비교",
        ],
        conflicts=["RULE_LINE_GENERAL_FORM"],
    ),
    RuleDefinition(
        rule_id="RULE_LINE_GENERAL_FORM",
        name="직선 일반형 ↔ 절편형",
        description="직선을 일반형/절편형/기울기형 간에 변환한다.",
        concepts=["직선"],
        preconditions=["직선"],
        changed_dimensions=[_REP, _DATA],
        construction_template="직선 y = mx + b 를 ax + by + c = 0 형태로 바꾸어 제시한다.",
        difficulty_delta=0.1,
        verifier_recipe=["sympy: 양식 동치 검증"],
        conflicts=["RULE_LINE_TWO_POINTS"],
    ),
    RuleDefinition(
        rule_id="RULE_CIRCLE_CENTER_RADIUS",
        name="원을 중심·반지름으로 표현",
        description="원의 방정식을 중심과 반지름 조건으로 재표현한다.",
        concepts=["원"],
        preconditions=["원"],
        changed_dimensions=[_REP, _CTX, _DATA],
        construction_template=(
            "원 (x-a)^2+(y-b)^2=r^2 을 '중심이 (a,b)이고 반지름이 r 인 원'으로 제시한다."
        ),
        difficulty_delta=0.2,
        verifier_recipe=["sympy: 중심·반지름 재구성 동치 검증"],
        conflicts=["RULE_CIRCLE_GENERAL_FORM"],
    ),
    RuleDefinition(
        rule_id="RULE_CIRCLE_GENERAL_FORM",
        name="원 일반형 ↔ 중심·반지름",
        description="원의 일반형 x^2+y^2+Dx+Ey+F=0 과 중심·반지름 표현을 변환한다.",
        concepts=["원"],
        preconditions=["원"],
        changed_dimensions=[_REP, _DATA],
        construction_template="원을 일반형으로 제시하고 중심·반지름을 구하게 한다.",
        difficulty_delta=0.3,
        verifier_recipe=[
            "sympy: 완전제곱식 완성 후 중심·반지름 비교",
        ],
        conflicts=["RULE_CIRCLE_CENTER_RADIUS"],
    ),
    RuleDefinition(
        rule_id="RULE_TANGENT_DISTANCE",
        name="접선을 거리 조건으로",
        description="접선을 중심-직선 거리 = 반지름 조건으로 표현한다.",
        concepts=["원", "접선", "거리"],
        preconditions=["원", "직선", "접선"],
        changed_dimensions=[_ROUTE, _REP, _AUX],
        construction_template=(
            "접선의 기울기/절편을 미지수로 두고 거리 조건으로 접선을 구하게 한다."
        ),
        difficulty_delta=0.3,
        verifier_recipe=[
            "sympy: 중심-직선 거리 == 반지름 검증",
            "numeric: 접점 수치 검증",
        ],
        conflicts=[],
    ),
    RuleDefinition(
        rule_id="RULE_TANGENT_DISCRIMINANT",
        name="접선을 판별식으로",
        description="접선을 이차방정식 판별식 = 0 조건으로 표현한다.",
        concepts=["원", "접선"],
        preconditions=["원", "직선", "접선"],
        changed_dimensions=[_ROUTE, _REP],
        construction_template=(
            "직선을 원의 방정식에 대입한 이차방정식의 판별식 D = 0 으로 접선을 구하게 한다."
        ),
        difficulty_delta=0.3,
        verifier_recipe=["sympy: 판별식 D == 0 검증", "numeric: 접점 존재 검증"],
        conflicts=["RULE_TANGENT_DISTANCE"],
    ),
    RuleDefinition(
        rule_id="RULE_OBJECTIVE_INVERSION",
        name="질문 역전",
        description="목표와 조건을 뒤집어(주어진 것 ↔ 구하는 것) 질문 방향을 바꾼다.",
        concepts=["방정식"],
        preconditions=["직선", "원"],
        changed_dimensions=[_OBJ, _ORDER, _CTX],
        construction_template="'접선을 구하라'를 '이 직선이 접선이 되도록 하는 값'으로 바꾼다.",
        difficulty_delta=0.4,
        verifier_recipe=["sympy: 역전된 목표의 해집합 동치 검증"],
        conflicts=[],
    ),
    RuleDefinition(
        rule_id="RULE_CONDITION_TOPOLOGY",
        name="조건 위상 변경",
        description="조건의 종속 구조(동시 조건 ↔ 단계 조건)를 재배치한다.",
        concepts=["방정식"],
        preconditions=["원", "직선"],
        changed_dimensions=[_LINE, _ORDER, _AUX],
        construction_template="복합 조건을 (1)(2) 단계로 나누거나 병합한다.",
        difficulty_delta=0.3,
        verifier_recipe=["sympy: 분해된 조건의 해집합 합집합 동치 검증"],
        conflicts=[],
    ),
    RuleDefinition(
        rule_id="RULE_TRANSLATION",
        name="평행이동 적용",
        description="도형을 평행이동하여 변환된 도형의 방정식을 구하게 한다.",
        concepts=["평행이동", "방정식"],
        preconditions=["평행이동"],
        changed_dimensions=[_DATA, _REP, _CTX],
        construction_template="원/직선을 (p,q)만큼 평행이동한 도형을 제시한다.",
        difficulty_delta=0.2,
        verifier_recipe=["sympy: 이동 후 중심/절편 검증"],
        conflicts=[],
    ),
    RuleDefinition(
        rule_id="RULE_REFLECTION",
        name="대칭이동 적용",
        description="도형을 x축·y축·원점·직선에 대하여 대칭이동한다.",
        concepts=["대칭이동", "방정식"],
        preconditions=["대칭이동"],
        changed_dimensions=[_DATA, _REP, _CTX],
        construction_template="원/직선을 주어진 축에 대칭이동한 도형을 제시한다.",
        difficulty_delta=0.2,
        verifier_recipe=["sympy: 대칭 이동 후 방정식 비교"],
        conflicts=[],
    ),
]


def rule_concepts(catalog: RuleCatalog) -> set[str]:
    """카탈로그의 모든 개념 ID 집합."""
    return {concept for rule in catalog.all_rules() for concept in rule.concepts}

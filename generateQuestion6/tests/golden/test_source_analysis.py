"""T02.4 — Source Analyzer 구조 추출 골드 테스트.

- T02.4-GT1: 원·직선 접선 문항에서 중심·반지름·직선·매개변수·목표가 정확히 추출된다.
- T02.4-GT2: 분모·근호·부호의 암묵 정의역이 누락되면 골드 비교가 실패한다.
- T02.4-GT3: 범위 밖 개념을 핵심 개념으로 추출하면 SCOPE_VIOLATION이다.
- T02.4-GT4: 모호한 자연어는 추측하지 않고 unresolved_assumptions를 생성한다.
- T02.4-GT5: 동일 입력 재실행 시 스키마와 핵심 필드가 안정적이다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from math_variant.domain.problem import ProblemSpec
from math_variant.domain.scope import ScopeProfile
from math_variant.errors import MathVariantError
from math_variant.services.geometry_parser import DeterministicSourceAnalyzer
from math_variant.services.source_analyzer import golden_compare

GOLDEN_DIR = Path(__file__).resolve().parent / "data" / "source_analysis"

_SCOPE = ScopeProfile(
    profile_id="p1",
    school_name="골드 테스트 학교",
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
    allowed_answer_types=["expression", "interval", "coordinate", "length", "area"],
)


def _load_golden(name: str) -> dict:
    return json.loads((GOLDEN_DIR / name).read_text(encoding="utf-8"))


def _analyze(normalized_text: str) -> ProblemSpec:
    return DeterministicSourceAnalyzer(_SCOPE).analyze(normalized_text)


def test_gt1_tangent_from_point() -> None:
    golden = _load_golden("golden-tangent-from-point.json")
    spec = _analyze(golden["normalized_text"])

    assert golden_compare(spec, golden["expected"]) is True, golden_compare.report(
        spec, golden["expected"]
    )
    assert "원" in spec.core_concepts
    assert "접선" in spec.core_concepts
    assert spec.objective.natural_language == "접선의 방정식을 구하시오"


def test_gt1_no_intersection_k_range() -> None:
    golden = _load_golden("golden-no-intersection-k-range.json")
    spec = _analyze(golden["normalized_text"])

    assert golden_compare(spec, golden["expected"]) is True, golden_compare.report(
        spec, golden["expected"]
    )
    assert "k" in spec.unknowns


def test_gt2_missing_implicit_domain_fails_golden_compare() -> None:
    golden = _load_golden("golden-radius-parameter-implicit-domain.json")
    spec = _analyze(golden["normalized_text"])

    assert "4 - k > 0" in spec.implicit_domain, spec.implicit_domain
    assert golden_compare(spec, golden["expected"]) is True

    # 암묵 정의역이 누락된 잘못된 추출 결과는 골드 비교에서 실패해야 한다.
    broken = spec.model_copy(update={"implicit_domain": []})
    assert golden_compare(broken, golden["expected"]) is False


def test_gt3_out_of_scope_core_concept_is_scope_violation() -> None:
    text = "로그함수 y = log x 의 그래프를 그리고 최댓값을 구하시오."
    with pytest.raises(MathVariantError) as exc_info:
        _analyze(text)
    assert exc_info.value.code == "SCOPE_VIOLATION"


def test_gt4_ambiguous_natural_language_creates_unresolved() -> None:
    ambiguous = "두 도형의 관계를 구하고 그 과정을 서술하시오."
    spec = _analyze(ambiguous)

    assert spec.has_unresolved_assumptions is True
    assert spec.unresolved_assumptions, "모호한 자연어를 추측해서는 안 된다"


def test_gt5_repeat_runs_are_stable() -> None:
    golden = _load_golden("golden-tangent-from-point.json")
    first = _analyze(golden["normalized_text"])
    second = _analyze(golden["normalized_text"])

    assert first.model_dump() == second.model_dump()
    assert set(first.model_dump().keys()) == set(second.model_dump().keys())

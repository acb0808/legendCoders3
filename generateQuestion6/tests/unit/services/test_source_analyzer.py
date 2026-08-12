"""T02.4 — Source Analyzer 단위 테스트 (LLM 경로 + LLM 출력 불변식)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from math_variant.domain.scope import ScopeProfile
from math_variant.errors import MathVariantError
from math_variant.providers.contracts import ProviderResponse, RolePolicy
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine
from math_variant.services.source_analyzer import ProblemSpecOutput, SourceAnalyzer

_SCOPE = ScopeProfile(
    profile_id="p1",
    school_name="테스트",
    exam_scope=["도형의 방정식"],
    allowed_units=["원의 방정식"],
    concept_vocabulary=["원", "직선", "접선", "좌표", "교점"],
    allowed_answer_types=["expression"],
)


class _Engine(StructuredOutputEngine):
    """LLM 응답을 직접 주입하는 테스트 엔진."""

    def __init__(self, data: dict) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self._data = data

    def generate_structured(self, request, policy=None) -> ProviderResponse:
        if request.role != RolePolicy.SOURCE_ANALYZER:
            raise AssertionError("Source Analyzer 는 source_analyzer 역할만 호출한다")
        return ProviderResponse(request_id=request.request_id, ok=True, data=self._data)


def _payload(**overrides: object) -> dict:
    base = {
        "core_concepts": ["원", "접선"],
        "auxiliary_concepts": [],
        "givens": [
            {"id": "circle", "natural_language": "원 x^2+y^2=8", "sympy_expr": "x**2+y**2-8"}
        ],
        "unknowns": [],
        "objective": {"id": "goal", "natural_language": "접선의 방정식을 구하시오"},
        "answer_type": "expression",
        "explicit_assumptions": [],
        "implicit_domain": [],
        "expected_methods": ["판별식"],
        "unresolved_assumptions": [],
    }
    base.update(overrides)
    return base


def test_llm_output_maps_to_spec_and_blocks_on_unresolved() -> None:
    analyzer = SourceAnalyzer(_Engine(_payload()), _SCOPE, "시스템 프롬프트")

    spec = analyzer.analyze("점 (1,3)에서 원 x^2+y^2=10에 그은 접선")
    assert spec.core_concepts == ["원", "접선"]
    assert spec.has_unresolved_assumptions is False

    analyzer_unresolved = SourceAnalyzer(
        _Engine(_payload(unresolved_assumptions=["원의 중심 좌표 미지정"])), _SCOPE, "p"
    )
    spec2 = analyzer_unresolved.analyze("...")
    assert spec2.has_unresolved_assumptions is True


def test_out_of_scope_concept_raises_scope_violation() -> None:
    analyzer = SourceAnalyzer(_Engine(_payload(core_concepts=["원", "로그"])), _SCOPE, "p")
    with pytest.raises(MathVariantError) as exc_info:
        analyzer.analyze("...")
    assert exc_info.value.code == "SCOPE_VIOLATION"


def test_engine_failure_raises_source_unresolved() -> None:
    class BrokenEngine(_Engine):
        def generate_structured(self, request, policy=None) -> ProviderResponse:
            return ProviderResponse(request_id=request.request_id, ok=False)

    analyzer = SourceAnalyzer(BrokenEngine({}), _SCOPE, "p")
    with pytest.raises(MathVariantError) as exc_info:
        analyzer.analyze("...")
    assert exc_info.value.code == "SOURCE_UNRESOLVED"


def test_output_schema_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ProblemSpecOutput.model_validate(_payload(injected_extra="field", core_concepts=["원"]))

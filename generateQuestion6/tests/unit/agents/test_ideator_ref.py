"""단위 테스트 — IdeatorAgent 기출 출제 패턴 섹션 주입 검증 (M4 TDD)."""

from __future__ import annotations

from typing import Any

from math_variant.agents.ideator import IdeatorAgent
from math_variant.agents.schemas import IdeationOutput
from math_variant.providers.contracts import ProviderResponse
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine

_IDEATION_DATA: dict[str, Any] = {
    "idea_id": "idea-1",
    "title": "질문 역전",
    "preserved_concepts": ["원의 방정식"],
    "changed_dimensions": ["objective", "data_domain"],
    "change_description": ["질문을 역전한다"],
    "construction_blueprint": "원과 직선의 위치 관계 변형",
}


class DummyIdeatorEngine(StructuredOutputEngine):
    """프롬프트를 캡처하는 테스트용 더미 엔진."""

    def __init__(self) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self.prompts: list[str] = []

    def generate_structured(self, request: Any, policy: Any = None) -> ProviderResponse:
        self.prompts.append(request.prompt)
        return ProviderResponse(request_id=request.request_id, ok=True, data=_IDEATION_DATA)


def test_ideator_agent_without_pattern_section() -> None:
    """pattern_section이 없을 때 기존과 동일한 프롬프트가 생성되는지 검증."""
    engine = DummyIdeatorEngine()
    agent = IdeatorAgent(engine, "IDEATOR_BUNDLE")
    output = agent.ideate("브리프", "seed-0")

    assert isinstance(output, IdeationOutput)
    expected = "IDEATOR_BUNDLE\n\n[입력]\n브리프"
    assert engine.prompts[0] == expected


def test_ideator_agent_with_pattern_section() -> None:
    """pattern_section이 주어졌을 때 [입력] 앞에 정확히 배치되는지 검증."""
    engine = DummyIdeatorEngine()
    agent = IdeatorAgent(engine, "IDEATOR_BUNDLE")
    pattern_sec = "[기출 출제 패턴 참조]\n1. [원의 방정식] 발문 형태: 원의 방정식을 구하시오"
    output = agent.ideate("브리프", "seed-0", pattern_section=pattern_sec)

    assert isinstance(output, IdeationOutput)
    expected = (
        "IDEATOR_BUNDLE\n\n"
        "[기출 출제 패턴 참조]\n1. [원의 방정식] 발문 형태: 원의 방정식을 구하시오\n\n"
        "[입력]\n브리프"
    )
    assert engine.prompts[0] == expected

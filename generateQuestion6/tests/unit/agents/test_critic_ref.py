"""단위 테스트 — CriticAgent 교육과정 정합 평가 섹션 주입 검증 (M3 TDD)."""

from __future__ import annotations

from typing import Any

from math_variant.agents.critic import CriticAgent
from math_variant.agents.schemas import CriticOutput
from math_variant.providers.contracts import ProviderResponse
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine

_CRITIC_DATA: dict[str, Any] = {
    "score": 8.5,
    "difficulty_estimate": "중상",
    "criteria_scores": {"difficulty": 4.0, "novelty": 4.5},
    "comments": ["우수함"],
    "recommendation": "PASS",
}


class DummyCriticEngine(StructuredOutputEngine):
    """프롬프트를 캡처하는 테스트용 더미 엔진."""

    def __init__(self) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self.prompts: list[str] = []

    def generate_structured(self, request: Any, policy: Any = None) -> ProviderResponse:
        self.prompts.append(request.prompt)
        return ProviderResponse(request_id=request.request_id, ok=True, data=_CRITIC_DATA)


def test_critic_agent_without_scope_section() -> None:
    """scope_section이 없을 때 기존과 동일한 프롬프트가 생성되는지 검증."""
    engine = DummyCriticEngine()
    agent = CriticAgent(engine, "CRITIC_BUNDLE")
    output = agent.criticize(
        problem_text="후보 문제",
        spec_brief="스펙",
        strategy_brief="전략",
    )

    assert isinstance(output, CriticOutput)
    expected = (
        "CRITIC_BUNDLE\n\n"
        "[문제 후보]\n후보 문제\n"
        "[문제 구조]\n스펙\n"
        "[변형 전략]\n전략"
    )
    assert engine.prompts[0] == expected


def test_critic_agent_with_scope_section() -> None:
    """scope_section이 있을 때 프롬프트 말미에 정확히 부착되는지 검증."""
    engine = DummyCriticEngine()
    agent = CriticAgent(engine, "CRITIC_BUNDLE")
    critic_scope = "[교육과정 정합 평가 기준]\n- 금지 개념: 지수, 로그"
    output = agent.criticize(
        problem_text="후보 문제",
        spec_brief="스펙",
        strategy_brief="전략",
        scope_section=critic_scope,
    )

    assert isinstance(output, CriticOutput)
    expected = (
        "CRITIC_BUNDLE\n\n"
        "[문제 후보]\n후보 문제\n"
        "[문제 구조]\n스펙\n"
        "[변형 전략]\n전략\n\n"
        "[교육과정 정합 평가 기준]\n- 금지 개념: 지수, 로그"
    )
    assert engine.prompts[0] == expected

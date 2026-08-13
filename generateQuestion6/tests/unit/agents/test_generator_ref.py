"""단위 테스트 — GeneratorAgent 조건 표현 관례 및 해설 스타일 주입 검증 (M4 TDD)."""

from __future__ import annotations

from typing import Any

from math_variant.agents.generator import GeneratorAgent
from math_variant.domain.candidate import CandidateProblem
from math_variant.providers.contracts import ProviderResponse
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine

_GENERATOR_DATA: dict[str, Any] = {
    "problem_text": "원 x^2+y^2=4 위의 점 (0,2)에서의 접선의 방정식을 구하시오.",
    "formalization": {"symbols": ["x", "y"], "constraints": ["x^2+y^2=4"], "goal": "접선의 방정식"},
    "final_answer_claim": "y=2",
    "solution_steps": [
        {"step_id": "1", "statement": "접선 공식 적용", "justification": "공식에 의해 y=2"}
    ],
    "transformation_evidence": [],
    "verification_script": "assert True",
    "needs_figure": False,
    "figure_notes": "",
}

_BLUEPRINT: dict[str, Any] = {
    "idea_id": "idea-0",
    "preserved_concepts": ["원의 방정식"],
    "changed_dimensions": ["objective"],
    "construction_blueprint": "원 위의 접선 구하기",
}


class DummyGeneratorEngine(StructuredOutputEngine):
    """프롬프트를 캡처하는 테스트용 더미 엔진."""

    def __init__(self) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self.prompts: list[str] = []

    def generate_structured(self, request: Any, policy: Any = None) -> ProviderResponse:
        self.prompts.append(request.prompt)
        return ProviderResponse(request_id=request.request_id, ok=True, data=_GENERATOR_DATA)


def test_generator_agent_without_sections() -> None:
    """조건/스타일 섹션이 없을 때 기존과 동일한 프롬프트가 생성되는지 검증."""
    engine = DummyGeneratorEngine()
    agent = GeneratorAgent(engine, "GENERATOR_BUNDLE")
    candidate, _output = agent.generate(
        candidate_id="cand-1",
        blueprint=_BLUEPRINT,
        brief="[브리프]",
    )

    assert candidate.problem_text.startswith("원")
    assert agent._last_prompt is not None
    assert "[조건 표현 관례 가이드]" not in agent._last_prompt
    assert "[해설 스타일 가이드" not in agent._last_prompt


def test_generator_agent_with_condition_and_style_sections() -> None:
    """조건 표현 관례 및 해설 스타일 섹션이 주어지면 [문제 생성] 앞단에 배치되는지 검증."""
    engine = DummyGeneratorEngine()
    agent = GeneratorAgent(engine, "GENERATOR_BUNDLE")
    cond_sec = "[조건 표현 관례]\n1. 빈출: 원 위의 점"
    style_sec = "[해설 스타일 가이드]\n- 서술: 주어진 원의"

    candidate, _output = agent.generate(
        candidate_id="cand-1",
        blueprint=_BLUEPRINT,
        brief="[브리프]",
        condition_section=cond_sec,
        style_section=style_sec,
    )

    assert isinstance(candidate, CandidateProblem)
    expected = (
        "GENERATOR_BUNDLE\n\n"
        "[조건 표현 관례]\n1. 빈출: 원 위의 점\n\n"
        "[해설 스타일 가이드]\n- 서술: 주어진 원의\n\n"
        "[문제 구조]\n[브리프]\n"
        "[승인 청사진]\n"
        "- 보존: ['원의 방정식']\n"
        "- 변경 차원: ['objective']\n"
        "- 구성 청사진: 원 위의 접선 구하기\n"
    )
    assert engine.prompts[0] == expected

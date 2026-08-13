"""단위 테스트 — PlannerAgent 교육과정 범위 주입 검증 (M3 TDD)."""

from __future__ import annotations

from typing import Any

from math_variant.agents.planner import PlannerAgent
from math_variant.agents.schemas import PlannerOutput
from math_variant.providers.contracts import ProviderResponse
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine

_PLANNER_DATA: dict[str, Any] = {
    "core_concepts": ["원의 방정식"],
    "auxiliary_concepts": [],
    "objective": "원의 중심과 반지름 구하기",
    "answer_type": "expression",
    "domain": "도형의 방정식",
    "preservation_goals": ["원의 기하학적 성질"],
    "forbidden_structure": ["직선 위 점에서 축에 수선"],
    "strategy": {
        "difficulty_target": "중",
        "preservation_goals": ["원의 성질"],
        "variation_direction": ["수치 변형"],
        "quality_criteria": ["명확성"],
    },
    "unresolved_assumptions": [],
}


class DummyPlannerEngine(StructuredOutputEngine):
    """프롬프트를 캡처하는 테스트용 더미 엔진."""

    def __init__(self) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self.prompts: list[str] = []

    def generate_structured(self, request: Any, policy: Any = None) -> ProviderResponse:
        self.prompts.append(request.prompt)
        return ProviderResponse(request_id=request.request_id, ok=True, data=_PLANNER_DATA)


def test_planner_agent_without_scope_section() -> None:
    """scope_section이 빈 문자열일 때 기존과 동일한 프롬프트가 생성되는지 검증."""
    engine = DummyPlannerEngine()
    agent = PlannerAgent(engine, "PROMPT_BUNDLE")
    output = agent.plan("원문 문제 텍스트")

    assert isinstance(output, PlannerOutput)
    assert engine.prompts[0] == "PROMPT_BUNDLE\n\n[원문]\n원문 문제 텍스트"


def test_planner_agent_with_scope_section() -> None:
    """scope_section이 주어졌을 때 [원문] 앞에 정확히 배치되는지 검증."""
    engine = DummyPlannerEngine()
    agent = PlannerAgent(engine, "PROMPT_BUNDLE")
    scope_sec = "[교육과정 허용 범위]\n- 허용: 원의 방정식"
    agent.plan("원문 문제 텍스트", difficulty_target="상", scope_section=scope_sec)

    expected = (
        "PROMPT_BUNDLE\n\n"
        "[교육과정 허용 범위]\n- 허용: 원의 방정식\n\n"
        "[원문]\n원문 문제 텍스트\n"
        "[난이도 목표]\n상"
    )
    assert engine.prompts[0] == expected

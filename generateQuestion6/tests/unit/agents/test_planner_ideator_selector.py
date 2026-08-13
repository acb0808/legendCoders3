"""T07 — 기획·발상·선별 에이전트 테스트."""

from __future__ import annotations

import pytest

from math_variant.agents.ideator import IdeatorAgent, build_ideation_brief
from math_variant.agents.planner import PlannerAgent
from math_variant.agents.schemas import (
    IdeationOutput,
    PlannerOutput,
    ProductionStrategy,
    SelectionOutput,
)
from math_variant.agents.selector import SelectorAgent
from math_variant.errors import MathVariantError
from math_variant.providers.contracts import ProviderResponse, RolePolicy
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine

_PLANNER_DATA = {
    "core_concepts": ["포물선", "평행이동", "직선"],
    "auxiliary_concepts": ["교점", "중점"],
    "objective": "상수의 값과 길이의 곱을 구하시오",
    "answer_type": "expression",
    "domain": "이차함수·도형의 이동",
    "preservation_goals": ["평행이동 성질", "교점·중점"],
    "forbidden_structure": ["직선 위 점에서 축에 수선", "삼각형 넓이 조건"],
    "strategy": {
        "difficulty_target": "중상",
        "preservation_goals": ["평행이동 성질"],
        "variation_direction": ["질문 역전", "조건 일반화"],
        "quality_criteria": ["유일해", "범위 내 개념"],
    },
    "unresolved_assumptions": [],
}

_IDEA = {
    "idea_id": "idea-1",
    "title": "질문 역전",
    "preserved_concepts": ["평행이동"],
    "changed_dimensions": ["objective", "condition_topology", "solution_route", "data_domain"],
    "change_description": ["질문을 역전한다"],
    "construction_blueprint": "a를 주고 조건을 만족하는 값을 구하게 한다",
}


class _Engine(StructuredOutputEngine):
    """역할별 고정 응답을 주입하는 테스트 엔진."""

    def __init__(self, data: dict, roles: set[str]) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self._data = data
        self._roles = roles
        self.calls: list[RolePolicy] = []
        self.prompts: list[str] = []

    def generate_structured(self, request, policy=None) -> ProviderResponse:
        self.calls.append(request.role)
        self.prompts.append(request.prompt)
        if request.role.value not in self._roles:
            raise AssertionError(f"예상치 못한 역할: {request.role}")
        return ProviderResponse(request_id=request.request_id, ok=True, data=self._data)


def test_planner_returns_strategy_and_rejects_original_text_in_strategy() -> None:
    engine = _Engine(_PLANNER_DATA, {"planner"})
    agent = PlannerAgent(engine=engine, prompt_bundle="기획 프롬프트")
    output = agent.plan("포물선 y=x^2-3x-8 을 평행이동 ...")

    assert isinstance(output, PlannerOutput)
    assert engine.calls == [RolePolicy.PLANNER]
    serialized = output.model_dump_json()
    assert "y=x^2-3x-8" not in serialized
    assert "포물선 y=x^2-3x-8" in engine.prompts[0]


def test_planner_engine_failure_raises() -> None:
    class Broken(_Engine):
        def generate_structured(self, request, policy=None) -> ProviderResponse:
            return ProviderResponse(request_id=request.request_id, ok=False)

    agent = PlannerAgent(engine=Broken(_PLANNER_DATA, {"planner"}), prompt_bundle="p")
    with pytest.raises(MathVariantError) as exc_info:
        agent.plan("원문")
    assert exc_info.value.code == "AGENT_UNRESOLVED"


def test_ideator_never_sees_original() -> None:
    engine = _Engine(_IDEA, {"ideator"})
    agent = IdeatorAgent(engine=engine, prompt_bundle="발상 프롬프트")
    brief = build_ideation_brief(
        core_concepts=["포물선", "평행이동"],
        objective="상수의 값과 길이의 곱을 구하시오",
        answer_type="expression",
        domain="이차함수·도형의 이동",
        preservation_goals=["평행이동 성질"],
        strategy=ProductionStrategy.model_validate(_PLANNER_DATA["strategy"]),
    )
    assert "y=x^2" not in brief
    idea = agent.ideate(brief, seed="a")
    assert isinstance(idea, IdeationOutput)
    assert "y=x^2" not in engine.prompts[0]


def test_ideation_brief_excludes_forbidden_structure() -> None:
    brief = build_ideation_brief(
        core_concepts=["포물선"],
        objective="o",
        answer_type="expression",
        domain="d",
        preservation_goals=["p"],
        strategy=ProductionStrategy.model_validate(_PLANNER_DATA["strategy"]),
    )
    assert "직선 위 점에서 수선" not in brief
    assert "재사용 금지" not in brief


def test_ideate_embeds_forbidden_structure_in_prompt() -> None:
    engine = _Engine(_IDEA, {"ideator"})
    agent = IdeatorAgent(engine=engine, prompt_bundle="발상 프롬프트")
    brief = build_ideation_brief(
        core_concepts=["포물선"],
        objective="o",
        answer_type="expression",
        domain="d",
        preservation_goals=["p"],
        strategy=ProductionStrategy.model_validate(_PLANNER_DATA["strategy"]),
    )
    agent.ideate(
        brief, seed="a", forbidden_structure=["직선 위 점에서 수선", "삼각형 넓이"]
    )
    assert "직선 위 점에서 수선" not in brief
    assert "금지 구조" in engine.prompts[0]
    assert "직선 위 점에서 수선" in engine.prompts[0]
    assert "삼각형 넓이" in engine.prompts[0]


def test_ideate_omits_forbidden_section_when_none() -> None:
    engine = _Engine(_IDEA, {"ideator"})
    agent = IdeatorAgent(engine=engine, prompt_bundle="발상 프롬프트")
    brief = build_ideation_brief(
        core_concepts=["포물선"],
        objective="o",
        answer_type="expression",
        domain="d",
        preservation_goals=["p"],
        strategy=ProductionStrategy.model_validate(_PLANNER_DATA["strategy"]),
    )
    agent.ideate(brief, seed="a")
    assert "금지 구조" not in engine.prompts[0]


def test_selector_adopts_ideas() -> None:
    engine = _Engine(
        {"adopted_ideas": ["idea-1", "idea-3"], "rationale": "전략 부합"},
        {"selector"},
    )
    agent = SelectorAgent(engine=engine, prompt_bundle="선별 프롬프트")
    ideas = [IdeationOutput.model_validate({**_IDEA, "idea_id": f"idea-{i}"}) for i in (1, 2, 3)]
    output = agent.select(ideas, "난이도 목표: 중상")
    assert isinstance(output, SelectionOutput)
    assert output.adopted_ideas == ["idea-1", "idea-3"]

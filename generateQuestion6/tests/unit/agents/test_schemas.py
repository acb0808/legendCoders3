"""T07 — 다중 에이전트 응답 스키마 불변식 테스트."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from math_variant.agents.schemas import (
    CodeReviewOutput,
    GeneratorOutput,
    IdeationOutput,
    JudgeOutput,
    PlannerOutput,
    VisionOutput,
    register_agent_schemas,
)
from math_variant.domain.transformation import Dimension
from math_variant.providers.registry import SchemaRegistry


def _planner(**overrides: object) -> dict:
    base = {
        "core_concepts": ["포물선", "평행이동", "직선"],
        "auxiliary_concepts": ["교점", "중점"],
        "objective": "중점이 주어진 직선 위에 있을 때 상수의 값을 구하시오",
        "answer_type": "expression",
        "domain": "이차함수·도형의 이동",
        "preservation_goals": ["평행이동 성질", "포물선과 직선의 교점"],
        "strategy": {
            "difficulty_target": "중상",
            "preservation_goals": ["평행이동 성질"],
            "variation_direction": ["질문 역전", "조건 일반화"],
            "quality_criteria": ["유일해", "범위 내 개념만"],
        },
        "unresolved_assumptions": [],
    }
    base.update(overrides)
    return base


def test_planner_schema_parses() -> None:
    output = PlannerOutput.model_validate(_planner())
    assert "포물선" in output.core_concepts
    assert output.strategy.difficulty_target == "중상"


def test_planner_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        PlannerOutput.model_validate(_planner(injected="extra"))


def test_ideation_dimension_coerces_from_string() -> None:
    data = {
        "idea_id": "idea-1",
        "title": "질문 역전",
        "preserved_concepts": ["평행이동"],
        "changed_dimensions": ["objective", "condition_topology"],
        "change_description": ["질문을 역전한다"],
        "construction_blueprint": "a를 주고 AB 길이를 구하게 한다",
        "figure_required": False,
    }
    output = IdeationOutput.model_validate(data)
    assert output.changed_dimensions == [Dimension.OBJECTIVE, Dimension.CONDITION_TOPOLOGY]


def test_generator_requires_verification_script() -> None:
    base = {
        "problem_text": "문제 본문",
        "formalization": {"symbols": ["x", "y"], "constraints": [], "goal": "a의 값"},
        "final_answer_claim": "8sqrt(2)",
        "solution_steps": [],
        "transformation_evidence": [],
    }
    with pytest.raises(ValidationError):
        GeneratorOutput.model_validate(base)
    output = GeneratorOutput.model_validate({**base, "verification_script": "result = {...}"})
    assert output.verification_script


def test_code_review_and_judge_schemas() -> None:
    review = CodeReviewOutput.model_validate(
        {"verdict": "APPROVE", "safe": True, "test_consistent": True, "feedback": ""}
    )
    assert review.verdict == "APPROVE"
    judge = JudgeOutput.model_validate(
        {"ranking": [{"candidate_id": "c1", "score": 8.0, "reason": "안전"}], "summary": ""}
    )
    assert judge.ranking[0]["candidate_id"] == "c1"


def test_vision_output_and_registry() -> None:
    vision = VisionOutput.model_validate({"tikz_code": r"\draw (0,0) -- (1,1);", "caption": ""})
    assert vision.tikz_code

    registry = SchemaRegistry()
    register_agent_schemas(registry)
    for name in (
        "PlannerOutput",
        "IdeationOutput",
        "SelectionOutput",
        "GeneratorOutput",
        "CodeReviewOutput",
        "CriticOutput",
        "JudgeOutput",
        "VisionOutput",
    ):
        assert name in registry._models

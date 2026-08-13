"""LangChain 문제 생성기 흐름 테스트 — 가짜 체인을 주입해 조립을 검증한다."""

from __future__ import annotations

import pytest
from langchain_core.runnables import Runnable, RunnableLambda

from math_variant.agents.schemas import (
    GeneratorOutput,
    IdeationOutput,
    PlannerOutput,
    ProductionStrategy,
)
from math_variant.domain.candidate import CandidateProblem, Formalization, SolutionStepClaim
from math_variant.domain.transformation import Dimension
from math_variant.langchain_generator.generator import LangChainProblemGenerator

_PLAN = PlannerOutput(
    core_concepts=["원", "직선의 위치 관계"],
    auxiliary_concepts=["접점"],
    objective="상수의 범위를 구하시오",
    answer_type="interval",
    domain="도형의 방정식",
    preservation_goals=["원과 직선의 위치 관계"],
    forbidden_structure=["접선의 방정식 구성", "거리 = 반지름 조건"],
    strategy=ProductionStrategy(
        difficulty_target="중상",
        preservation_goals=["원과 직선의 위치 관계"],
        variation_direction=["질문 역전", "조건 위상 변경"],
        quality_criteria=["유일해"],
        constraints=[],
    ),
    unresolved_assumptions=[],
)

_IDEA = IdeationOutput(
    idea_id="idea-7",
    title="할선 상황으로 재구성",
    preserved_concepts=["원", "직선"],
    changed_dimensions=[Dimension.OBJECTIVE, Dimension.CONDITION_TOPOLOGY],
    change_description=["접선 상황을 두 점에서 만나는 직선 상황으로 바꾼다"],
    construction_blueprint="판별식 D>0 경로로 k의 범위를 도출",
    figure_required=False,
    figure_notes="",
)

_GENERATOR = GeneratorOutput(
    problem_text="원과 직선이 서로 다른 두 점에서 만나도록 하는 k의 범위를 구하시오.",
    formalization=Formalization(
        symbols=["k"], constraints=["D>0"], goal="k의 범위", domain="도형의 방정식"
    ),
    final_answer_claim="-5<k<5",
    solution_steps=[SolutionStepClaim(step_id="s1", statement="판별식을 계산한다")],
    transformation_evidence=[{"dimension": "objective", "description": "질문 역전"}],
    verification_script="print('ok')",
    needs_figure=False,
    figure_notes="",
)


def _fake_chain[T: (PlannerOutput, IdeationOutput, GeneratorOutput)](
    output: T, calls: list[dict[str, str]]
) -> Runnable[dict[str, str], T]:
    """고정 응답을 반환하고 입력을 캡처하는 가짜 체인."""

    def _run(payload: dict[str, str]) -> T:
        calls.append(payload)
        return output

    return RunnableLambda(_run)


def _build(calls: dict[str, list[dict[str, str]]]) -> LangChainProblemGenerator:
    """캡처 목록이 달린 생성기를 만든다."""
    return LangChainProblemGenerator(
        planner_chain=_fake_chain(_PLAN, calls["planner"]),
        ideator_chain=_fake_chain(_IDEA, calls["ideator"]),
        generator_chain=_fake_chain(_GENERATOR, calls["generator"]),
    )


_SOURCE = "원 x^2+y^2=25 위의 점 (3,4) 에서의 접선의 방정식을 구하시오."


def test_generate_assembles_candidate_from_chain_outputs() -> None:
    """planner→ideator→generator 출력이 CandidateProblem 으로 올바르게 조립되어야 한다."""
    calls: dict[str, list[dict[str, str]]] = {"planner": [], "ideator": [], "generator": []}
    generator = _build(calls)

    result = generator.generate(_SOURCE, difficulty_target="중상", seed="cand-1")

    assert isinstance(result.candidate, CandidateProblem)
    assert result.plan == _PLAN
    assert result.idea == _IDEA
    assert result.generator_output == _GENERATOR

    candidate = result.candidate
    assert candidate.candidate_id == "cand-1"
    assert candidate.plan_id == "plan-idea-7"
    assert candidate.problem_text == _GENERATOR.problem_text
    assert candidate.formalization == _GENERATOR.formalization
    assert candidate.final_answer_claim == _GENERATOR.final_answer_claim
    assert candidate.solution_steps == _GENERATOR.solution_steps
    assert candidate.transformation_evidence == _GENERATOR.transformation_evidence
    assert candidate.verification_status == "UNVERIFIED"


def test_planner_input_contains_source_and_difficulty() -> None:
    """planner human 입력에는 원문과 난이도 목표가 담겨야 한다."""
    calls: dict[str, list[dict[str, str]]] = {"planner": [], "ideator": [], "generator": []}
    _build(calls).generate(_SOURCE, difficulty_target="중상")

    planner_input = calls["planner"][0]["input"]
    assert "[원문]" in planner_input
    assert _SOURCE in planner_input
    assert "[난이도 목표]" in planner_input
    assert "중상" in planner_input


def test_ideator_never_sees_original_text() -> None:
    """원문 분리 원칙 — ideator 입력에 원문 본문이 포함되지 않아야 한다."""
    calls: dict[str, list[dict[str, str]]] = {"planner": [], "ideator": [], "generator": []}
    _build(calls).generate(_SOURCE)

    ideator_input = calls["ideator"][0]["input"]
    assert _SOURCE not in ideator_input
    assert "[금지 구조 (원본 구성 골격, 재사용 금지)]" in ideator_input
    assert "접선의 방정식 구성" in ideator_input
    for concept in _PLAN.core_concepts:
        assert concept in ideator_input


def test_generator_input_contains_blueprint_and_forbidden_structure() -> None:
    """generator human 입력에는 승인 청사진 값과 금지 구조가 담겨야 한다."""
    calls: dict[str, list[dict[str, str]]] = {"planner": [], "ideator": [], "generator": []}
    _build(calls).generate(_SOURCE)

    generator_input = calls["generator"][0]["input"]
    assert "[문제 구조]" in generator_input
    assert "[승인 청사진]" in generator_input
    assert _IDEA.construction_blueprint in generator_input
    assert "objective" in generator_input
    assert "[금지 구조 (원본 구성 골격, 재사용 금지)]" in generator_input
    assert "거리 = 반지름 조건" in generator_input


def test_generate_default_seed_is_idea_0() -> None:
    """seed 를 주지 않으면 candidate_id 는 기본값 idea-0 이어야 한다."""
    calls: dict[str, list[dict[str, str]]] = {"planner": [], "ideator": [], "generator": []}
    result = _build(calls).generate(_SOURCE)
    assert result.candidate.candidate_id == "idea-0"


@pytest.mark.live_provider
def test_live_generation_smoke() -> None:
    """실제 공급자 호출 스모크 테스트 (기본 skip, MATH_VARIANT_LIVE_PROVIDER_TESTS=1 일 때 실행)."""
    from math_variant.langchain_generator.generator import build_langchain_generator

    generator = build_langchain_generator()
    result = generator.generate(_SOURCE, difficulty_target="중상")
    assert result.candidate.problem_text
    assert result.candidate.final_answer_claim

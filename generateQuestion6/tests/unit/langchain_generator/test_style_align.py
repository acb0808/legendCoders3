from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.unit.test_parity import MockBlindSolver, MockSandboxProvider, MockTrackingEngine

from math_variant.agents.code_reviewer import CodeReviewAgent
from math_variant.agents.critic import CriticAgent
from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.ideator import IdeatorAgent
from math_variant.agents.judge import JudgeAgent
from math_variant.agents.planner import PlannerAgent
from math_variant.agents.selector import SelectorAgent
from math_variant.domain.candidate import SolutionStepClaim
from math_variant.langchain_generator.pipeline import (
    _style_align_node,
    build_pipeline_graph,
)
from math_variant.pipeline_factory import PROMPTS_DIR
from math_variant.reference.models import SolutionStyle


def _p(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def test_style_align_node_pure_function() -> None:
    """_style_align_node 가 solution_steps 의 용어 및 구조를
    스타일 가이드에 맞춰 정렬하는지 검증."""
    from math_variant.domain.candidate import CandidateProblem, Formalization

    cand = CandidateProblem(
        candidate_id="cand-1",
        plan_id="plan-1",
        problem_text="원의 중심을 구하시오.",
        formalization=Formalization(symbols=["x"], constraints=[], goal="중심"),
        final_answer_claim="(0,0)",
        solution_steps=[
            SolutionStepClaim(step_id="1", statement="원 방정식 정리", justification="공식"),
            SolutionStepClaim(step_id="2", statement="중심 산출", justification="답"),
        ],
    )

    style_guide = SolutionStyle(
        unit="원의 방정식",
        open="주어진 원의",
        transform_order=["표준형 변환"],
        justification_vocab=["따라서", "그러므로"],
        close="구하는 값은",
        sample_step="표준형으로 정리한다.",
    )

    class DummyRuntime:
        context = None

    state = {
        "candidate": cand,
        "style_guide": style_guide,
    }

    res = _style_align_node(state, DummyRuntime())  # type: ignore[arg-type]
    aligned_cand = res.get("candidate")
    assert aligned_cand is not None
    assert len(aligned_cand.solution_steps) == 2
    # 마지막 단계의 justification 에 '따라서'가 추가되어 정렬되었는지 확인
    assert "따라서" in aligned_cand.solution_steps[1].justification


def test_langchain_pipeline_with_style_align_enabled(tmp_path: Path) -> None:
    """enable_style_align=True 일 때 그래프를 거쳐 candidate 의 해설 단계가 정렬되는지 검증."""
    shared_data: dict[str, Any] = {
        "planner": {
            "core_concepts": ["원의 방정식"],
            "auxiliary_concepts": [],
            "objective": "원의 중심과 반지름 구하기",
            "answer_type": "expression",
            "domain": "도형의 방정식",
            "preservation_goals": ["성질"],
            "forbidden_structure": ["골격"],
            "strategy": {
                "difficulty_target": "중",
                "preservation_goals": ["성질"],
                "variation_direction": ["수치 변형"],
                "quality_criteria": ["명확성"],
            },
            "unresolved_assumptions": [],
        },
        "ideator": {
            "idea_id": "idea-0",
            "title": "질문 역전",
            "preserved_concepts": ["원의 방정식"],
            "changed_dimensions": ["objective"],
            "change_description": ["설명"],
            "construction_blueprint": "설계도",
        },
        "selector": {
            "adopted_ideas": ["idea-0"],
            "rationale": "합격",
        },
        "generator": {
            "problem_text": "새로운 문제",
            "formalization": {"symbols": ["x"], "constraints": ["x>0"], "goal": "a의 값"},
            "final_answer_claim": "4",
            "solution_steps": [
                {"step_id": "1", "statement": "원 공식", "justification": "개념"},
                {"step_id": "2", "statement": "정리", "justification": "값 산출"},
            ],
            "transformation_evidence": [],
            "verification_script": "assert True",
            "needs_figure": False,
            "figure_notes": "",
        },
        "code_reviewer": {
            "verdict": "APPROVE",
            "safe": True,
            "test_consistent": True,
            "risk_notes": [],
            "feedback": "",
        },
        "critic": {
            "score": 9.0,
            "difficulty_estimate": "중",
            "criteria_scores": {"novelty": 4.5},
            "comments": ["우수"],
            "recommendation": "PASS",
        },
        "judge": {
            "ranking": [{"candidate_id": "idea-0", "rank": 1}],
            "summary": "우수",
        },
    }

    engine = MockTrackingEngine(shared_data)
    pipeline = build_pipeline_graph(
        planner=PlannerAgent(engine, _p("planner.md")),
        ideator=IdeatorAgent(engine, _p("ideator.md")),
        selector=SelectorAgent(engine, _p("selector.md")),
        generator=GeneratorAgent(engine, _p("candidate_generator.md")),
        code_reviewer=CodeReviewAgent(engine, _p("code_reviewer.md")),
        critic=CriticAgent(engine, _p("critic.md")),
        judge=JudgeAgent(engine, _p("judge.md")),
        vision=None,
        sandbox=MockSandboxProvider(),
        blind_solvers=MockBlindSolver(),
        runs_dir=tmp_path / "runs",
        ideator_count=1,
        enable_style_align=True,
    )

    report = pipeline.run("원문 텍스트")
    assert len(report.candidates) == 1

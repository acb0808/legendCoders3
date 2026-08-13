from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.unit.test_parity import MockBlindSolver, MockSandboxProvider, MockTrackingEngine

from math_variant.agents.pipeline import AgentPipeline
from math_variant.domain.candidate import SolutionStepClaim
from math_variant.langchain_generator.pipeline import build_pipeline_graph
from math_variant.reference.knowledge_graph import (
    KnowledgeConcept,
    KnowledgeIndex,
    assign_skill_ids,
)


def test_assign_skill_ids_direct() -> None:
    """assign_skill_ids 함수가 풀이 단계에 skill_id를 정확히 부여하는지 검증."""
    index = KnowledgeIndex(
        skills={
            "원의 방정식": KnowledgeConcept(
                id=101, name="원의 방정식", semester="고1", description="원"
            )
        }
    )
    steps = [
        SolutionStepClaim(
            step_id="S1",
            statement="원의 방정식 공식 (x-a)^2+(y-b)^2=r^2 을 적용한다.",
            justification="원 정의",
        ),
        SolutionStepClaim(
            step_id="S2", statement="방정식을 정리하여 답을 구한다.", justification="대수 계산"
        ),
    ]

    evidences = assign_skill_ids(steps, concepts=["원의 방정식"], knowledge_index=index)
    assert len(evidences) == 2
    assert evidences[0]["dimension"] == "skill_mapping"
    assert evidences[0]["step_id"] == "S1"
    assert evidences[0]["skill_id"] == "101"
    assert evidences[0]["concept_name"] == "원의 방정식"

    assert evidences[1]["dimension"] == "skill_mapping"
    assert evidences[1]["step_id"] == "S2"
    assert evidences[1]["skill_id"] is None
    assert evidences[1]["reason"] == "no_match"


def test_agent_pipeline_attaches_skill_mapping_evidence(tmp_path: Path) -> None:
    """AgentPipeline 실행 시 생성된 후보의
    transformation_evidence에 skill_mapping이 추가되는지 검증."""
    from math_variant.agents.code_reviewer import CodeReviewAgent
    from math_variant.agents.critic import CriticAgent
    from math_variant.agents.generator import GeneratorAgent
    from math_variant.agents.ideator import IdeatorAgent
    from math_variant.agents.judge import JudgeAgent
    from math_variant.agents.planner import PlannerAgent
    from math_variant.agents.selector import SelectorAgent
    from math_variant.pipeline_factory import PROMPTS_DIR

    def _p(name: str) -> str:
        return (PROMPTS_DIR / name).read_text(encoding="utf-8")

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
            "problem_text": "새로운 원의 방정식 문제",
            "formalization": {"symbols": ["x"], "constraints": ["x>0"], "goal": "a의 값"},
            "final_answer_claim": "4",
            "solution_steps": [
                {
                    "step_id": "1",
                    "statement": "원의 방정식 표준형을 적용한다.",
                    "justification": "개념 적용",
                }
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
    pipeline = AgentPipeline(
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
    )

    report = pipeline.run("원문 텍스트")
    assert len(report.candidates) == 1
    cand = report.candidates[0].candidate
    skill_ev = [ev for ev in cand.transformation_evidence if ev.get("dimension") == "skill_mapping"]
    assert len(skill_ev) >= 1
    assert skill_ev[0]["step_id"] == "1"


def test_langchain_pipeline_attaches_skill_mapping_evidence(tmp_path: Path) -> None:
    """LangChainPipeline 실행 시 생성된 후보의
    transformation_evidence에 skill_mapping이 추가되는지 검증."""
    from math_variant.agents.code_reviewer import CodeReviewAgent
    from math_variant.agents.critic import CriticAgent
    from math_variant.agents.generator import GeneratorAgent
    from math_variant.agents.ideator import IdeatorAgent
    from math_variant.agents.judge import JudgeAgent
    from math_variant.agents.planner import PlannerAgent
    from math_variant.agents.selector import SelectorAgent
    from math_variant.pipeline_factory import PROMPTS_DIR

    def _p(name: str) -> str:
        return (PROMPTS_DIR / name).read_text(encoding="utf-8")

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
            "problem_text": "새로운 원의 방정식 문제",
            "formalization": {"symbols": ["x"], "constraints": ["x>0"], "goal": "a의 값"},
            "final_answer_claim": "4",
            "solution_steps": [
                {
                    "step_id": "1",
                    "statement": "원의 방정식 표준형을 적용한다.",
                    "justification": "개념 적용",
                }
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
    )

    report = pipeline.run("원문 텍스트")
    assert len(report.candidates) == 1
    cand = report.candidates[0].candidate
    skill_ev = [ev for ev in cand.transformation_evidence if ev.get("dimension") == "skill_mapping"]
    assert len(skill_ev) >= 1
    assert skill_ev[0]["step_id"] == "1"

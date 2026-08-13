"""단위 테스트 — httpx AgentPipeline 과 LangChainPipeline 간 프롬프트 100% 일치 검증 (M4 TDD)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from math_variant.agents.pipeline import AgentPipeline
from math_variant.langchain_generator.pipeline import build_pipeline_graph
from math_variant.pipeline_factory import _resolve_scope_sections
from math_variant.providers.contracts import ProviderResponse
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine
from math_variant.reference.condition_retriever import ConditionStyleRetriever
from math_variant.reference.exam_retriever import ExamPatternRetriever
from math_variant.reference.sections import build_reference_runnable
from math_variant.reference.style_retriever import SolutionStyleRetriever
from math_variant.services.blind_solver import BlindConsensus, BlindSolver


class MockTrackingEngine(StructuredOutputEngine):
    """모든 역할의 호출 프롬프트를 기록하는 모의 엔진."""

    def __init__(self, data_by_role: dict[str, Any]) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self.data_by_role = data_by_role
        self.captured_prompts: dict[str, list[str]] = {}

    def generate_structured(self, request: Any, policy: Any = None) -> ProviderResponse:
        role_name = request.role.value if hasattr(request.role, "value") else str(request.role)
        if role_name not in self.captured_prompts:
            self.captured_prompts[role_name] = []
        self.captured_prompts[role_name].append(request.prompt)
        return ProviderResponse(
            request_id=request.request_id,
            ok=True,
            data=self.data_by_role.get(role_name, {}),
        )


class MockBlindSolver(BlindSolver):
    """모의 블라인드 솔버."""

    def __init__(self) -> None:
        pass

    def solve_both(self, problem_text: str) -> BlindConsensus:
        return BlindConsensus(
            status="PASS",
            solver_a="y=2",
            solver_b="y=2",
            reason="일치",
        )


class MockSandboxProvider:
    """모의 샌드박스 프로바이더."""

    def execute(self, request: Any) -> Any:
        from math_variant.sandbox.contracts import SandboxResult, SandboxStatus

        return SandboxResult(
            result_id="res-1",
            request_id=getattr(request, "request_id", "req-1"),
            status=SandboxStatus.COMPLETED,
            stdout="OK",
            stderr="",
            duration_ms=10,
            output_json={"result": {"verdict": "PASS", "detail": "OK"}},
        )


def _setup_test_reference_assets(tmp_path: Path) -> Any:
    exam_path = tmp_path / "reference_exam_patterns.jsonl"
    exam_card = {
        "topic_id": "C08-01-03-01",
        "unit": "원의 방정식",
        "pattern": "원",
        "wording": "구하시오",
        "condition_style": ["원 _"],
        "example_abstract": "원",
        "difficulty_zone": "중",
        "source_count": 1,
        "sources": [],
    }
    with open(exam_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(exam_card) + "\n")

    cond_path = tmp_path / "condition_style_index.json"
    cond_data = {
        "C08-01-03-01": {
            "topic_id": "C08-01-03-01",
            "unit": "원의 방정식",
            "condition_phrasings": [{"pattern": "원 _", "freq": 3}],
            "wording_conventions": ["구하시오"],
        }
    }
    with open(cond_path, "w", encoding="utf-8") as f:
        json.dump(cond_data, f)

    style_path = tmp_path / "solution_style_guide.json"
    style_data = {
        "원의 방정식": {
            "unit": "원의 방정식",
            "style": {
                "open": "열기",
                "transform_order": ["순서"],
                "justification_vocab": ["따라서"],
                "close": "닫기",
                "sample_step": "예시",
            },
        }
    }
    with open(style_path, "w", encoding="utf-8") as f:
        json.dump(style_data, f)

    exam_retriever = ExamPatternRetriever(index_path=exam_path, k=3)
    cond_retriever = ConditionStyleRetriever(index_path=cond_path, k=5)
    style_retriever = SolutionStyleRetriever(index_path=style_path)
    return build_reference_runnable(exam_retriever, cond_retriever, style_retriever)


def test_agent_pipeline_and_langchain_pipeline_prompt_parity(tmp_path: Path) -> None:
    """AgentPipeline 과 LangChainPipeline 에 동일한 참조 자산 및 입력을 주었을 때
    에이전트별 프롬프트가 문자 단위로 100% 동일한지 검증."""
    runnable = _setup_test_reference_assets(tmp_path)
    scope_sec, critic_sec = _resolve_scope_sections(scope_profile="off")

    shared_data: dict[str, Any] = {
        "planner": {
            "core_concepts": ["C08-01-03-01", "원의 방정식"],
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
            "solution_steps": [{"step_id": "1", "statement": "풀이", "justification": "이유"}],
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

    # 1. httpx AgentPipeline 실행
    engine_httpx = MockTrackingEngine(shared_data)
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

    pipeline_httpx = AgentPipeline(
        planner=PlannerAgent(engine_httpx, _p("planner.md")),
        ideator=IdeatorAgent(engine_httpx, _p("ideator.md")),
        selector=SelectorAgent(engine_httpx, _p("selector.md")),
        generator=GeneratorAgent(engine_httpx, _p("candidate_generator.md")),
        code_reviewer=CodeReviewAgent(engine_httpx, _p("code_reviewer.md")),
        critic=CriticAgent(engine_httpx, _p("critic.md")),
        judge=JudgeAgent(engine_httpx, _p("judge.md")),
        vision=None,
        sandbox=MockSandboxProvider(),  # type: ignore[arg-type]
        blind_solvers=MockBlindSolver(),
        runs_dir=tmp_path / "runs_httpx",
        ideator_count=1,
        reference_runnable=runnable,
        scope_section=scope_sec,
        critic_scope_section=critic_sec,
    )
    pipeline_httpx.run("원문 문제 텍스트")

    # 2. LangChainPipeline 실행
    engine_lc = MockTrackingEngine(shared_data)
    pipeline_lc = build_pipeline_graph(
        planner=PlannerAgent(engine_lc, _p("planner.md")),
        ideator=IdeatorAgent(engine_lc, _p("ideator.md")),
        selector=SelectorAgent(engine_lc, _p("selector.md")),
        generator=GeneratorAgent(engine_lc, _p("candidate_generator.md")),
        code_reviewer=CodeReviewAgent(engine_lc, _p("code_reviewer.md")),
        critic=CriticAgent(engine_lc, _p("critic.md")),
        judge=JudgeAgent(engine_lc, _p("judge.md")),
        vision=None,
        sandbox=MockSandboxProvider(),  # type: ignore[arg-type]
        blind_solvers=MockBlindSolver(),
        runs_dir=tmp_path / "runs_lc",
        ideator_count=1,
        scope_section=scope_sec,
        critic_scope_section=critic_sec,
        reference_runnable=runnable,
    )
    pipeline_lc.run("원문 문제 텍스트")

    # 3. 100% 문자 단위 프롬프트 일치 검증
    for role in ["planner", "ideator", "candidate_generator", "critic"]:
        httpx_prompts = engine_httpx.captured_prompts.get(role, [])
        lc_prompts = engine_lc.captured_prompts.get(role, [])

        assert len(httpx_prompts) == len(lc_prompts), f"{role} 호출 횟수 불일치"
        for i, (hp, lp) in enumerate(zip(httpx_prompts, lc_prompts, strict=True)):
            assert hp == lp, f"{role} 프롬프트 {i}번째 불일치!\nHTTPX:\n{hp}\n---\nLC:\n{lp}"

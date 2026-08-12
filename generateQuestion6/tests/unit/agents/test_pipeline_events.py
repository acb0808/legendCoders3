"""T08 — 파이프라인이 단계 이벤트를 방출하는지 테스트."""

from __future__ import annotations

from pathlib import Path

from math_variant.agents.code_reviewer import CodeReviewAgent
from math_variant.agents.critic import CriticAgent
from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.ideator import IdeatorAgent
from math_variant.agents.judge import JudgeAgent
from math_variant.agents.pipeline import AgentPipeline
from math_variant.agents.planner import PlannerAgent
from math_variant.agents.selector import SelectorAgent
from math_variant.events import EventStage, PipelineEvent
from math_variant.providers.contracts import ProviderResponse, RolePolicy
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine
from math_variant.sandbox.contracts import SandboxResult, SandboxStatus
from math_variant.services.blind_solver import BlindConsensus

_PLANNER = {
    "core_concepts": ["포물선", "평행이동"],
    "auxiliary_concepts": [],
    "objective": "상수의 값을 구하시오",
    "answer_type": "expression",
    "domain": "도형의 방정식",
    "preservation_goals": ["평행이동 성질"],
    "strategy": {
        "difficulty_target": "중상",
        "preservation_goals": ["평행이동"],
        "variation_direction": ["질문 역전"],
        "quality_criteria": ["유일해"],
    },
    "unresolved_assumptions": [],
}
_IDEA = {
    "idea_id": "idea-1",
    "title": "질문 역전",
    "preserved_concepts": ["평행이동"],
    "changed_dimensions": ["objective", "condition_topology", "solution_route", "data_domain"],
    "change_description": ["역전"],
    "construction_blueprint": "a를 구하게 한다",
}
_CANDIDATE = {
    "problem_text": "문제 본문",
    "formalization": {"symbols": ["x"], "constraints": [], "goal": "a의 값"},
    "final_answer_claim": "8sqrt(2)",
    "solution_steps": [{"step_id": "s1", "statement": "단계"}],
    "transformation_evidence": [{"dimension": "objective", "description": "역전"}],
    "verification_script": "result = {'verdict': 'PASS'}",
}
_REVIEW = {"verdict": "APPROVE", "safe": True, "test_consistent": True, "feedback": ""}
_CRITIC = {
    "score": 8.0,
    "difficulty_estimate": "중상",
    "criteria_scores": {},
    "comments": [],
    "recommendation": "PASS",
}
_JUDGE = {"ranking": [{"candidate_id": "cand-1", "score": 8.0, "reason": "통과"}], "summary": ""}


class _Engine(StructuredOutputEngine):
    def __init__(self, responses: dict[str, list[dict]]) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self.responses = {k: list(v) for k, v in responses.items()}
        self.calls: list[tuple[RolePolicy, str]] = []

    def generate_structured(self, request, policy=None) -> ProviderResponse:
        self.calls.append((request.role, request.prompt))
        queue = self.responses.get(request.role.value, [])
        if not queue:
            return ProviderResponse(request_id=request.request_id, ok=False)
        data = queue.pop(0)
        return ProviderResponse(request_id=request.request_id, ok=True, data=data)


class _PassSandbox:
    name = "fake"

    def execute(self, request) -> SandboxResult:
        return SandboxResult(
            result_id="r",
            request_id=request.request_id,
            status=SandboxStatus.COMPLETED,
            output_json={"result": {"verdict": "PASS"}},
        )


class _PassSolvers:
    def solve_both(self, problem_text: str) -> BlindConsensus:
        return BlindConsensus(status="PASS", solver_a="A", solver_b="B", reason="동치")


def _build_pipeline(engine: _Engine, tmp_path: Path, on_event) -> AgentPipeline:
    return AgentPipeline(
        planner=PlannerAgent(engine, "p"),
        ideator=IdeatorAgent(engine, "p"),
        selector=SelectorAgent(engine, "p"),
        generator=GeneratorAgent(engine, "p"),
        code_reviewer=CodeReviewAgent(engine, "p"),
        critic=CriticAgent(engine, "p"),
        judge=JudgeAgent(engine, "p"),
        vision=None,
        sandbox=_PassSandbox(),  # type: ignore[arg-type]
        blind_solvers=_PassSolvers(),  # type: ignore[arg-type]
        runs_dir=tmp_path,
        max_workers=4,
        max_refine=1,
        ideator_count=1,
        on_event=on_event,
    )


def test_pipeline_emits_stage_events_in_order(tmp_path) -> None:
    engine = _Engine(
        {
            "planner": [_PLANNER],
            "ideator": [_IDEA],
            "selector": [{"adopted_ideas": ["idea-1"], "rationale": "부합"}],
            "generator": [_CANDIDATE],
            "code_reviewer": [_REVIEW],
            "critic": [_CRITIC],
            "judge": [_JUDGE],
        }
    )
    events: list[PipelineEvent] = []
    _build_pipeline(engine, tmp_path, events.append).run("원문")

    stages = [e.stage for e in events]
    assert EventStage.PLANNER in stages
    assert EventStage.IDEATION in stages
    assert EventStage.SELECTION in stages
    assert EventStage.GENERATION in stages
    assert EventStage.CODE_REVIEW in stages
    assert EventStage.SANDBOX in stages
    assert EventStage.BLIND in stages
    assert EventStage.CRITIC in stages
    assert EventStage.JUDGE in stages
    assert EventStage.DONE in stages
    # 마지막은 done(완료)
    assert events[-1].stage == EventStage.DONE
    assert events[-1].status == "done"


def test_pipeline_emits_sandbox_and_candidate_scoped_events(tmp_path) -> None:
    engine = _Engine(
        {
            "planner": [_PLANNER],
            "ideator": [_IDEA],
            "selector": [{"adopted_ideas": ["idea-1"], "rationale": "부합"}],
            "generator": [_CANDIDATE],
            "code_reviewer": [_REVIEW],
            "critic": [_CRITIC],
            "judge": [_JUDGE],
        }
    )
    events: list[PipelineEvent] = []
    _build_pipeline(engine, tmp_path, events.append).run("원문")

    sandbox_events = [e for e in events if e.stage == EventStage.SANDBOX]
    assert sandbox_events
    assert sandbox_events[0].status == "started"
    assert sandbox_events[1].status == "done"
    assert sandbox_events[0].candidate_id == "cand-1"

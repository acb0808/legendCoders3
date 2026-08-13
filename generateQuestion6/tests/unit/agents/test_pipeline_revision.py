"""T06 — 파이프라인 원문 유사성 피드백 루프 테스트.

결정적 유사성 필터(services.similarity)가 원문과 같은 표현을 생성한 후보를
재생성(REVISE 유사 루트)으로 돌리고, 재시도 한도를 넘으면 폐기(UNRESOLVED)하는지 검증한다.
"""

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

_SOURCE_TEXT = (
    "포물선 y=x^2-4x+3 위의 점 P에서 접선을 그었다. "
    "점 P에서의 접선과 x축이 만나는 점의 좌표를 구하시오."
)

_PLANNER = {
    "core_concepts": ["포물선", "접선", "좌표"],
    "auxiliary_concepts": [],
    "objective": "접점에서의 접선과 x축이 만나는 점의 좌표를 구하시오",
    "answer_type": "coordinate",
    "domain": "이차함수와 접선",
    "preservation_goals": ["접선의 성질"],
    "forbidden_structure": ["접선과 x축의 교점 좌표"],
    "strategy": {
        "difficulty_target": "중",
        "preservation_goals": ["접선의 성질"],
        "variation_direction": ["질문 역전"],
        "quality_criteria": ["유일해"],
    },
    "unresolved_assumptions": [],
}

_IDEA = {
    "idea_id": "idea-1",
    "title": "질문 역전",
    "preserved_concepts": ["포물선"],
    "changed_dimensions": ["objective", "condition_topology", "data_domain"],
    "change_description": ["접선 조건을 교점 조건으로 역전"],
    "construction_blueprint": "접선 대신 교점 조건을 이용하게 바꾼다",
}

_CANDIDATE = {
    "problem_text": (
        "포물선 y=(x-2)^2-1 과 직선 y=x 가 서로 다른 두 점 A, B 에서 만난다. "
        "중점이 x=3 위에 있을 때 a의 값과 AB 길이의 곱을 구하시오."
    ),
    "formalization": {"symbols": ["x", "a"], "constraints": [], "goal": "a의 값"},
    "final_answer_claim": "8sqrt(2)",
    "solution_steps": [{"step_id": "s1", "statement": "대입"}],
    "transformation_evidence": [{"dimension": "objective", "description": "역전"}],
    "verification_script": "result = {'verdict': 'PASS'}",
}

_CANDIDATE_SIMILAR = {**_CANDIDATE, "problem_text": _SOURCE_TEXT}

_REVIEW = {"verdict": "APPROVE", "safe": True, "test_consistent": True, "feedback": ""}
_CRITIC = {
    "score": 8.0,
    "difficulty_estimate": "중",
    "criteria_scores": {"novelty": 8, "clarity": 9, "pedagogy": 8, "difficulty_consistency": 7},
    "comments": [],
    "recommendation": "PASS",
}
_JUDGE = {
    "ranking": [{"candidate_id": "cand-1", "score": 8.0, "reason": "검증 통과"}],
    "summary": "채택",
}


class _Engine(StructuredOutputEngine):
    """역할별 응답을 순차 큐로 주입하는 테스트 엔진."""

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


def _pipeline(
    engine: _Engine,
    tmp_path: Path,
    max_refine: int,
    on_event=None,
) -> AgentPipeline:
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
        max_refine=max_refine,
        ideator_count=1,
        on_event=on_event,
    )


def _base_responses(generator: list[dict]) -> dict[str, list[dict]]:
    return {
        "planner": [_PLANNER],
        "ideator": [_IDEA],
        "selector": [{"adopted_ideas": ["idea-1"], "rationale": "부합"}],
        "generator": generator,
        "code_reviewer": [_REVIEW],
        "critic": [_CRITIC],
        "judge": [_JUDGE],
    }


def test_similar_candidate_triggers_retry_and_succeeds(tmp_path) -> None:
    """원문과 동일한 후보는 재생성 루트로 돌아가고, 다음 시도에서 PASS 한다."""
    engine = _Engine(_base_responses([_CANDIDATE_SIMILAR, _CANDIDATE]))
    events: list[PipelineEvent] = []
    pipeline = _pipeline(engine, tmp_path, max_refine=2, on_event=events.append)
    report = pipeline.run(_SOURCE_TEXT)

    assert len(report.candidates) == 1
    assert report.candidates[0].attempts == 2
    assert report.candidates[0].status == "PASS"
    failed = [e for e in events if e.stage == EventStage.GENERATION and e.status == "failed"]
    assert len(failed) == 1
    assert "유사" in failed[0].message
    assert failed[0].candidate_id == "cand-1"


def test_similar_candidate_discarded_at_max_refine(tmp_path) -> None:
    """재시도 한도 소진 시 유사 후보를 UNRESOLVED 로 폐기한다."""
    engine = _Engine(
        _base_responses([_CANDIDATE_SIMILAR])
    )
    pipeline = _pipeline(engine, tmp_path, max_refine=1)
    report = pipeline.run(_SOURCE_TEXT)

    assert len(report.candidates) == 1
    assert report.candidates[0].status == "UNRESOLVED"
    assert report.candidates[0].attempts == 1


def test_empty_source_skips_similarity_filter(tmp_path) -> None:
    """source_text 가 비어 있으면 유사성 필터는 재생성을 트리거하지 않는다."""
    engine = _Engine(
        _base_responses([_CANDIDATE_SIMILAR])
    )
    pipeline = _pipeline(engine, tmp_path, max_refine=1)
    report = pipeline.run("")

    assert len(report.candidates) == 1
    assert report.candidates[0].status == "PASS"
    assert report.candidates[0].attempts == 1

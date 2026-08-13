"""T07 — 파이프라인 오케스트레이터 테스트 (병렬·게이트·개선 루프)."""

from __future__ import annotations

from pathlib import Path

from math_variant.agents.blind import LLMBlindSolver
from math_variant.agents.code_reviewer import CodeReviewAgent
from math_variant.agents.critic import CriticAgent
from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.ideator import IdeatorAgent
from math_variant.agents.judge import JudgeAgent
from math_variant.agents.pipeline import AgentPipeline
from math_variant.agents.planner import PlannerAgent
from math_variant.agents.selector import SelectorAgent
from math_variant.providers.contracts import ProviderResponse, RolePolicy
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine
from math_variant.sandbox.contracts import SandboxResult, SandboxStatus
from math_variant.services.blind_solver import BlindConsensus, BlindSolution

_PLANNER = {
    "core_concepts": ["포물선", "평행이동", "직선"],
    "auxiliary_concepts": ["교점", "중점"],
    "objective": "상수의 값과 길이의 곱을 구하시오",
    "answer_type": "expression",
    "domain": "이차함수·도형의 이동",
    "preservation_goals": ["평행이동 성질"],
    "forbidden_structure": ["직선 위 점에서 축에 수선", "삼각형 넓이 조건"],
    "strategy": {
        "difficulty_target": "중상",
        "preservation_goals": ["평행이동 성질"],
        "variation_direction": ["질문 역전"],
        "quality_criteria": ["유일해"],
    },
    "unresolved_assumptions": [],
}

_IDEAS = [
    {
        "idea_id": "idea-1",
        "title": "질문 역전",
        "preserved_concepts": ["평행이동"],
        "changed_dimensions": ["objective", "condition_topology", "solution_route", "data_domain"],
        "change_description": ["질문 역전"],
        "construction_blueprint": "중점 조건을 이용해 a를 구한다",
    },
    {
        "idea_id": "idea-2",
        "title": "직선 일반화",
        "preserved_concepts": ["평행이동", "교점"],
        "changed_dimensions": ["condition_topology", "data_domain", "objective", "solution_route"],
        "change_description": ["직선을 y=x+k 로 일반화"],
        "construction_blueprint": "직선 기울기를 매개화해 교점 조건을 바꾼다",
    },
]

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

_REVIEW_OK = {"verdict": "APPROVE", "safe": True, "test_consistent": True, "feedback": ""}
_REVIEW_REVISE = {
    "verdict": "REVISE",
    "safe": True,
    "test_consistent": False,
    "feedback": "검증 스크립트가 답을 검증하지 않는다",
}
_CRITIC = {
    "score": 8.0,
    "difficulty_estimate": "중상",
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


class _FailSandbox:
    name = "fake-fail"

    def execute(self, request) -> SandboxResult:
        return SandboxResult(
            result_id="r",
            request_id=request.request_id,
            status=SandboxStatus.COMPLETED,
            output_json={"result": {"verdict": "FAIL"}},
        )


class _PassSolvers:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def solve_both(self, problem_text: str) -> BlindConsensus:
        self.calls.append(problem_text)
        return BlindConsensus(status="PASS", solver_a="A", solver_b="B", reason="동치")


def _build_engine() -> _Engine:
    return _Engine(
        {
            "planner": [_PLANNER],
            "ideator": [_IDEAS[0], _IDEAS[1]],
            "selector": [{"adopted_ideas": ["idea-1", "idea-2"], "rationale": "부합"}],
            "generator": [_CANDIDATE, _CANDIDATE],
            "code_reviewer": [_REVIEW_OK, _REVIEW_OK],
            "critic": [_CRITIC, _CRITIC],
            "judge": [_JUDGE],
        }
    )


def _pipeline(engine: _Engine, tmp_path: Path, max_refine: int = 1) -> AgentPipeline:
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
        ideator_count=2,
    )


def test_pipeline_produces_passing_candidate(tmp_path) -> None:
    engine = _build_engine()
    report = _pipeline(engine, tmp_path).run("원문...")

    assert report.run_id
    passed = [v for v in report.candidates if v.test_outcome and v.test_outcome.passes]
    assert len(passed) == 2
    for v in passed:
        assert v.status == "PASS"
    assert report.ranking[0]["candidate_id"] in {v.candidate.candidate_id for v in passed}


def test_pipeline_source_never_leaks_to_ideators(tmp_path) -> None:
    engine = _build_engine()
    _pipeline(engine, tmp_path).run("기밀 원문 본문 Q19")
    for role, prompt in engine.calls:
        if role in {RolePolicy.IDEATOR, RolePolicy.SELECTOR, RolePolicy.GENERATOR}:
            assert "기밀 원문 본문" not in prompt


def test_pipeline_refines_revise_candidates(tmp_path) -> None:
    engine = _Engine(
        {
            "planner": [_PLANNER],
            "ideator": [_IDEAS[0], _IDEAS[1]],
            "selector": [{"adopted_ideas": ["idea-1"], "rationale": "부합"}],
            "generator": [_CANDIDATE, _CANDIDATE],
            "code_reviewer": [_REVIEW_REVISE, _REVIEW_OK],
            "critic": [_CRITIC, _CRITIC],
            "judge": [_JUDGE],
        }
    )
    report = _pipeline(engine, tmp_path, max_refine=2).run("원문")
    assert any(v.attempts >= 2 for v in report.candidates)
    assert all(v.status == "PASS" for v in report.candidates)


def test_pipeline_writes_report_and_uses_blind(tmp_path) -> None:
    engine = _build_engine()
    pipeline = _pipeline(engine, tmp_path)
    pipeline.run("원문")
    out = tmp_path / "report.json"
    assert out.is_file()
    assert pipeline.blind_calls == 2  # 후보 2건


def test_pipeline_fail_closed_when_sandbox_returns_fail(tmp_path) -> None:
    engine = _build_engine()
    pipeline = _pipeline(engine, tmp_path)
    pipeline.sandbox = _FailSandbox()  # type: ignore[assignment]
    report = pipeline.run("원문")
    for v in report.candidates:
        assert v.status == "FAIL"
        assert v.candidate.verification_status == "FAIL"


def test_pipeline_reject_review_is_terminal_unresolved(tmp_path) -> None:
    engine = _Engine(
        {
            "planner": [_PLANNER],
            "ideator": [_IDEAS[0], _IDEAS[1]],
            "selector": [{"adopted_ideas": ["idea-1"], "rationale": "부합"}],
            "generator": [_CANDIDATE],
            "code_reviewer": [
                {"verdict": "REJECT", "safe": False, "test_consistent": False, "feedback": "폐기"}
            ],
            "critic": [_CRITIC, _CRITIC],
            "judge": [_JUDGE],
        }
    )
    report = _pipeline(engine, tmp_path, max_refine=2).run("원문")
    assert len(report.candidates) == 1
    assert report.candidates[0].status == "UNRESOLVED"
    assert report.candidates[0].attempts == 1


def test_pipeline_revise_exhausts_bound_to_unresolved(tmp_path) -> None:
    engine = _Engine(
        {
            "planner": [_PLANNER],
            "ideator": [_IDEAS[0], _IDEAS[1]],
            "selector": [{"adopted_ideas": ["idea-1"], "rationale": "부합"}],
            "generator": [_CANDIDATE, _CANDIDATE],
            "code_reviewer": [_REVIEW_REVISE, _REVIEW_REVISE],
            "critic": [_CRITIC, _CRITIC],
            "judge": [_JUDGE],
        }
    )
    report = _pipeline(engine, tmp_path, max_refine=2).run("원문")
    assert report.candidates[0].attempts == 2
    assert report.candidates[0].status == "UNRESOLVED"


def test_pipeline_renders_figure_when_required(tmp_path) -> None:
    from math_variant.agents.vision_artist import VisionArtist

    engine = _Engine(
        {
            "planner": [_PLANNER],
            "ideator": [_IDEAS[0], _IDEAS[1]],
            "selector": [{"adopted_ideas": ["idea-1", "idea-2"], "rationale": "부합"}],
            "generator": [{**_CANDIDATE, "needs_figure": True}, _CANDIDATE],
            "code_reviewer": [_REVIEW_OK, _REVIEW_OK],
            "critic": [_CRITIC, _CRITIC],
            "judge": [_JUDGE],
            "vision": [{"tikz_code": r"\draw (0,0) -- (1,1);", "caption": ""}],
        }
    )
    figures = tmp_path / "figures"
    pipeline = _pipeline(engine, tmp_path)
    pipeline.vision = VisionArtist(engine, "v", figures)
    pipeline.run("원문")
    assert (figures / "cand-1.tex").is_file()
    assert not (figures / "cand-2.tex").exists()


def test_pipeline_forwards_difficulty_target_to_planner(tmp_path) -> None:
    engine = _build_engine()
    _pipeline(engine, tmp_path).run("원문", difficulty_target="상")
    planner_prompt = next(p for role, p in engine.calls if role == RolePolicy.PLANNER)
    assert "난이도 목표" in planner_prompt
    assert "상" in planner_prompt


def test_pipeline_continues_when_one_ideator_fails(tmp_path) -> None:
    """병렬 발상 중 일부만 성공해도 진행한다 (발상은 선택적)."""
    engine = _Engine(
        {
            "planner": [_PLANNER],
            # ideator 큐에 1개만 두면 ideator_count=2 중 하나는 ok=False 로 실패한다
            "ideator": [_IDEAS[0]],
            "selector": [{"adopted_ideas": ["idea-1"], "rationale": "부합"}],
            "generator": [_CANDIDATE],
            "code_reviewer": [_REVIEW_OK],
            "critic": [_CRITIC],
            "judge": [_JUDGE],
        }
    )
    report = _pipeline(engine, tmp_path).run("원문")
    assert len(report.ideas) == 1
    assert report.ideas[0].idea_id == "idea-1"
    assert report.candidates
    assert report.candidates[0].status == "PASS"


def test_pipeline_fails_when_all_ideators_fail(tmp_path) -> None:
    """발상이 전부 실패하면 AGENT_UNRESOLVED 로 실패한다."""
    from math_variant.errors import MathVariantError

    engine = _Engine(
        {
            "planner": [_PLANNER],
            "ideator": [],  # 전부 실패
            "selector": [],
            "generator": [],
            "code_reviewer": [],
            "critic": [],
            "judge": [],
        }
    )
    try:
        _pipeline(engine, tmp_path).run("원문")
    except MathVariantError as exc:
        assert exc.code == "AGENT_UNRESOLVED"
    else:
        raise AssertionError("발상 전부 실패 시 예외가 발생해야 한다")


def test_pipeline_continues_when_one_candidate_generation_fails(tmp_path) -> None:
    """후보 생성·검증 중 하나만 실패해도 성공한 후보로 진행한다 (생성도 선택적)."""
    engine = _Engine(
        {
            "planner": [_PLANNER],
            "ideator": [_IDEAS[0], _IDEAS[1]],
            "selector": [{"adopted_ideas": ["idea-1", "idea-2"], "rationale": "부합"}],
            # generator 큐에 1개만 두면 cand-2 의 generate 는 ok=False 로 실패한다
            "generator": [_CANDIDATE],
            "code_reviewer": [_REVIEW_OK],
            "critic": [_CRITIC],
            "judge": [_JUDGE],
        }
    )
    report = _pipeline(engine, tmp_path).run("원문")
    assert len(report.candidates) == 1
    assert report.candidates[0].candidate.candidate_id == "cand-1"
    assert report.candidates[0].status == "PASS"


def test_pipeline_fails_when_all_candidates_fail(tmp_path) -> None:
    """모든 후보 생성·검증이 실패하면 AGENT_UNRESOLVED 로 실패한다."""
    from math_variant.errors import MathVariantError

    engine = _Engine(
        {
            "planner": [_PLANNER],
            "ideator": [_IDEAS[0]],
            "selector": [{"adopted_ideas": ["idea-1"], "rationale": "부합"}],
            "generator": [],  # 전부 실패
            "code_reviewer": [],
            "critic": [],
            "judge": [],
        }
    )
    try:
        _pipeline(engine, tmp_path).run("원문")
    except MathVariantError as exc:
        assert exc.code == "AGENT_UNRESOLVED"
    else:
        raise AssertionError("후보 전부 실패 시 예외가 발생해야 한다")


def test_llm_blind_solver_uses_blind_role_and_returns_solution() -> None:
    engine = _Engine(
        {
            "blind_solver": [
                {"answer_set": ["8sqrt(2)"], "domain": [], "key_steps": [], "status": "SATISFIABLE"}
            ]
        }
    )
    solver = LLMBlindSolver(engine=engine, prompt_bundle="블라인드 프롬프트", solver_id="A")
    solution = solver.solve("포물선 y=x^2 과 직선 y=x ...")
    assert isinstance(solution, BlindSolution)
    assert solution.solver_id == "A"
    assert solution.answer_set == ["8sqrt(2)"]
    assert engine.calls[0][0] == RolePolicy.BLIND_SOLVER

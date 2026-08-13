"""T07 — 생성·코드리뷰·비평·집계·도형 에이전트 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest

from math_variant.agents.code_reviewer import CodeReviewAgent
from math_variant.agents.critic import CriticAgent
from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.judge import JudgeAgent
from math_variant.agents.schemas import (
    CodeReviewOutput,
    CriticOutput,
    JudgeOutput,
)
from math_variant.agents.vision_artist import VisionArtist
from math_variant.domain.candidate import CandidateProblem
from math_variant.errors import MathVariantError
from math_variant.providers.contracts import ProviderResponse, RolePolicy
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine

_BLUEPRINT = {
    "title": "질문 역전",
    "preserved_concepts": ["평행이동"],
    "changed_dimensions": ["objective", "condition_topology", "solution_route", "data_domain"],
    "change_description": ["질문을 역전한다"],
    "construction_blueprint": "a를 주고 조건을 만족하는 값을 구하게 한다",
}

_CANDIDATE = {
    "problem_text": "포물선 y=(x-2)^2-1 과 직선 y=x 가 서로 다른 두 점에서 만난다...",
    "formalization": {"symbols": ["x", "a"], "constraints": [], "goal": "a의 값"},
    "final_answer_claim": "8sqrt(2)",
    "solution_steps": [{"step_id": "s1", "statement": "대입 후 판별식"}],
    "transformation_evidence": [{"dimension": "objective", "description": "역전"}],
    "verification_script": "from sympy import symbols\nresult = {'verdict': 'PASS'}",
    "needs_figure": True,
    "figure_notes": "포물선과 직선, 교점 A, B 표시",
}

_REVIEW = {"verdict": "APPROVE", "safe": True, "test_consistent": True, "feedback": ""}
_CRITIC = {
    "score": 8.0,
    "difficulty_estimate": "중상",
    "criteria_scores": {"novelty": 8, "clarity": 9, "pedagogy": 8, "difficulty_consistency": 7},
    "comments": ["구조적 변형이 충분하다"],
    "recommendation": "PASS",
}
_JUDGE = {
    "ranking": [{"candidate_id": "c1", "score": 8.0, "reason": "검증 통과"}],
    "summary": "1건 채택",
}


class _Engine(StructuredOutputEngine):
    def __init__(self, data: dict, roles: set[str]) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self._data = data
        self._roles = roles
        self.calls: list[RolePolicy] = []
        self.prompts: list[str] = []

    def generate_structured(self, request, policy=None) -> ProviderResponse:
        self.calls.append(request.role)
        self.prompts.append(request.prompt)
        assert request.role.value in self._roles
        return ProviderResponse(request_id=request.request_id, ok=True, data=self._data)


class _FakeEngine(StructuredOutputEngine):
    def __init__(self) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self._data = _CANDIDATE
        self._roles = {"generator"}

    def generate_structured(self, request, policy=None) -> ProviderResponse:
        return ProviderResponse(request_id=request.request_id, ok=True, data=self._data)


class _BrokenEngine(StructuredOutputEngine):
    def __init__(self, data: dict, roles: set[str]) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self._data = data
        self._roles = roles

    def generate_structured(self, request, policy=None) -> ProviderResponse:
        return ProviderResponse(request_id=request.request_id, ok=False)


def test_generator_assembles_candidate_with_script() -> None:
    engine = _Engine(_CANDIDATE, {"generator"})
    agent = GeneratorAgent(engine=engine, prompt_bundle="생성 프롬프트")
    candidate, extra = agent.generate(candidate_id="cand-1", blueprint=_BLUEPRINT, brief="브리프")
    assert isinstance(candidate, CandidateProblem)
    assert extra.verification_script.startswith("from sympy")
    assert extra.needs_figure is True
    assert engine.calls == [RolePolicy.GENERATOR]


def test_generator_refine_includes_feedback_in_prompt() -> None:
    engine = _Engine(_CANDIDATE, {"generator"})
    agent = GeneratorAgent(engine=engine, prompt_bundle="생성 프롬프트")
    agent.generate(
        candidate_id="cand-2",
        blueprint=_BLUEPRINT,
        brief="브리프",
        feedback="검증 스크립트가 거짓 테스트다",
    )
    assert "검증 스크립트가 거짓 테스트다" in agent._last_prompt


def test_generator_prompt_includes_forbidden_structure() -> None:
    agent = GeneratorAgent(_FakeEngine(), "생성 프롬프트")
    agent.generate(
        candidate_id="cand-1",
        blueprint={
            "idea_id": "idea-0",
            "preserved_concepts": ["p"],
            "changed_dimensions": ["objective"],
            "construction_blueprint": "b",
        },
        brief="문제 구조",
        forbidden_structure=["직선 위 점에서 수선", "삼각형 넓이"],
    )
    assert "직선 위 점에서 수선" in agent._last_prompt
    assert "재사용 금지" in agent._last_prompt


def test_generator_prompt_without_forbidden_structure() -> None:
    agent = GeneratorAgent(_FakeEngine(), "생성 프롬프트")
    agent.generate(
        candidate_id="cand-1",
        blueprint={
            "idea_id": "idea-0",
            "preserved_concepts": ["p"],
            "changed_dimensions": ["objective"],
            "construction_blueprint": "b",
        },
        brief="문제 구조",
    )
    assert "금지 구조" not in agent._last_prompt


def test_code_reviewer_returns_review() -> None:
    engine = _Engine(_REVIEW, {"code_reviewer"})
    agent = CodeReviewAgent(engine=engine, prompt_bundle="심사 프롬프트")
    review = agent.review("script", "문제 본문", "8sqrt(2)", candidate_id="cand-1")
    assert isinstance(review, CodeReviewOutput)
    assert review.approves


def test_critic_and_judge() -> None:
    engine = _Engine(_CRITIC, {"critic"})
    critic = CriticAgent(engine=engine, prompt_bundle="비평 프롬프트")
    assert isinstance(critic.criticize("문제", "스펙", "전략", candidate_id="cand-1"), CriticOutput)

    engine_j = _Engine(_JUDGE, {"judge"})
    judge = JudgeAgent(engine=engine_j, prompt_bundle="집계 프롬프트")
    result = judge.judge([{"candidate_id": "c1", "score": 8.0}], run_id="run-1")
    assert isinstance(result, JudgeOutput)


def test_vision_artist_writes_tikz(tmp_path) -> None:
    engine = _Engine(
        {"tikz_code": "```python\n\\draw (0,0) -- (1,1);\n```", "caption": "포물선"}, {"vision"}
    )
    artist = VisionArtist(engine=engine, prompt_bundle="도형 프롬프트", figures_dir=tmp_path)
    path = artist.render("cand-1", figure_notes="포물선과 직선")
    text = path.read_text(encoding="utf-8")
    assert path.name == "cand-1.tex"
    assert text.startswith("%")
    assert "```" not in text
    assert "\\draw (0,0) -- (1,1);" in text


def test_all_agents_raise_agent_unresolved_on_engine_failure() -> None:
    cases = [
        ("generator", lambda e: GeneratorAgent(e, "p").generate("cand-1", _BLUEPRINT, "브리프")),
        ("code_reviewer", lambda e: CodeReviewAgent(e, "p").review("s", "q", "a")),
        ("critic", lambda e: CriticAgent(e, "p").criticize("q", "스펙", "전략")),
        ("judge", lambda e: JudgeAgent(e, "p").judge([{"candidate_id": "c1"}])),
        ("vision", lambda e: VisionArtist(e, "p", Path("tmp")).render("cand-1", "노트")),
    ]
    for name, call in cases:
        with pytest.raises(MathVariantError) as exc_info:
            call(_BrokenEngine({}, set()))
        assert exc_info.value.code == "AGENT_UNRESOLVED", name

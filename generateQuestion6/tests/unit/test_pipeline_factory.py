"""T08 — 파이프라인 팩토리 테스트."""

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
from math_variant.pipeline_factory import build_agent_pipeline


def test_build_agent_pipeline_returns_configured_pipeline(tmp_path: Path) -> None:
    pipeline = build_agent_pipeline(
        ideator_count=2,
        max_refine=1,
        on_event=None,
        runs_dir=tmp_path,
        figures_dir=tmp_path / "figures",
        sandbox_image="math-variant-sandbox:test",
    )
    assert isinstance(pipeline, AgentPipeline)
    assert isinstance(pipeline.planner, PlannerAgent)
    assert isinstance(pipeline.ideator, IdeatorAgent)
    assert isinstance(pipeline.selector, SelectorAgent)
    assert isinstance(pipeline.generator, GeneratorAgent)
    assert isinstance(pipeline.code_reviewer, CodeReviewAgent)
    assert isinstance(pipeline.critic, CriticAgent)
    assert isinstance(pipeline.judge, JudgeAgent)
    assert pipeline.vision is not None
    assert pipeline.sandbox.name == "docker"
    assert pipeline.blind_solvers is not None
    assert pipeline.ideator_count == 2
    assert pipeline.max_refine == 1


def test_build_agent_pipeline_forwards_on_event_to_engine_and_pipeline(tmp_path: Path) -> None:
    emitted: list[object] = []
    on_event = emitted.append
    pipeline = build_agent_pipeline(
        ideator_count=1,
        max_refine=0,
        on_event=on_event,
        runs_dir=tmp_path,
        figures_dir=tmp_path / "figures",
    )
    assert pipeline.on_event is on_event
    engine = pipeline.planner.engine
    assert getattr(engine, "on_event", None) is on_event
    assert pipeline.blind_solvers.solver_a.engine is engine
    assert pipeline.blind_solvers.solver_b.engine is engine

"""T08 — 파이프라인 팩토리 테스트."""

from __future__ import annotations

from pathlib import Path

from math_variant.agents.pipeline import AgentPipeline
from math_variant.pipeline_factory import build_agent_pipeline


def test_build_agent_pipeline_returns_configured_pipeline(tmp_path: Path) -> None:
    pipeline = build_agent_pipeline(
        source_text="원문 본문",
        difficulty_target="중상",
        ideator_count=2,
        max_refine=1,
        on_event=None,
        runs_dir=tmp_path,
        figures_dir=tmp_path / "figures",
        sandbox_image="math-variant-sandbox:test",
    )
    assert isinstance(pipeline, AgentPipeline)
    assert pipeline.ideator_count == 2
    assert pipeline.max_refine == 1


def test_build_agent_pipeline_forwards_difficulty() -> None:
    pipeline = build_agent_pipeline(
        source_text="x",
        difficulty_target="상",
        ideator_count=1,
        max_refine=0,
        on_event=None,
        runs_dir=Path("runs"),
        figures_dir=Path("runs/figures"),
    )
    assert isinstance(pipeline, AgentPipeline)

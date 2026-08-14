"""파이프라인 팩토리 — CLI·웹(API)이 공용으로 사용하는 파이프라인 구성.

기본 httpx 파이프라인(AgentPipeline) 및 LangChain 파이프라인(LangChainPipeline)을
동일한 인터페이스로 생성·교체할 수 있다.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, Protocol

from langchain_core.runnables import Runnable

from math_variant.agents.blind import LLMBlindSolver
from math_variant.agents.code_reviewer import CodeReviewAgent
from math_variant.agents.critic import CriticAgent
from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.ideator import IdeatorAgent
from math_variant.agents.judge import JudgeAgent
from math_variant.agents.pipeline import AgentPipeline, PipelineReport
from math_variant.agents.planner import PlannerAgent
from math_variant.agents.schemas import register_agent_schemas
from math_variant.agents.selector import SelectorAgent
from math_variant.agents.vision_artist import VisionArtist
from math_variant.events import PipelineEvent
from math_variant.providers.factory import build_provider_registry
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.resolver import RoleResolver
from math_variant.providers.settings import ProviderSettings
from math_variant.providers.structured import StructuredOutputEngine
from math_variant.reference.condition_retriever import ConditionStyleRetriever
from math_variant.reference.curriculum import build_scope
from math_variant.reference.exam_retriever import ExamPatternRetriever
from math_variant.reference.sections import (
    build_reference_runnable,
)
from math_variant.reference.sections import (
    critic_scope_section as render_critic_scope,
)
from math_variant.reference.sections import (
    planner_scope_section as render_planner_scope,
)
from math_variant.reference.style_retriever import SolutionStyleRetriever
from math_variant.sandbox.provider import DockerSandboxProvider
from math_variant.services.blind_solver import BlindSolver

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class PipelineRunnerProtocol(Protocol):
    """파이프라인 실행자 프로토콜 (AgentPipeline 과 LangChainPipeline 공통)."""

    def run(
        self, source_text: str, strategy_brief: str = "", difficulty_target: str = ""
    ) -> PipelineReport: ...


def _resolve_scope_sections(
    scope_profile: str | None = None,
    scope_section: str | None = None,
    critic_scope_section: str | None = None,
) -> tuple[str, str]:
    if scope_section is not None and critic_scope_section is not None:
        return scope_section, critic_scope_section

    profile = (
        scope_profile
        if scope_profile is not None
        else os.getenv("MATH_VARIANT_SCOPE", "geometry").strip().lower()
    )
    if profile == "off":
        return "", ""

    include_sets = profile in ("with_sets", "full")
    include_functions = profile == "full"
    scope = build_scope(include_sets=include_sets, include_functions=include_functions)
    resolved_scope = scope_section if scope_section is not None else render_planner_scope(scope)
    resolved_critic = (
        critic_scope_section if critic_scope_section is not None else render_critic_scope(scope)
    )
    return resolved_scope, resolved_critic


def _resolve_reference_runnable(
    data_dir: Path | None = None,
) -> Runnable[dict[str, str], dict[str, Any]] | None:
    if os.getenv("MATH_VARIANT_REFERENCE", "on").strip().lower() == "off":
        return None
    d = data_dir or DEFAULT_DATA_DIR
    exam_p = d / "reference_exam_patterns.jsonl"
    cond_p = d / "condition_style_index.json"
    style_p = d / "solution_style_guide.json"
    if not (exam_p.exists() or cond_p.exists() or style_p.exists()):
        return None

    return build_reference_runnable(
        ExamPatternRetriever(index_path=exam_p, k=3),
        ConditionStyleRetriever(index_path=cond_p, k=5),
        SolutionStyleRetriever(index_path=style_p),
    )


def build_agent_pipeline(
    *,
    ideator_count: int = 3,
    max_refine: int = 2,
    on_event: Callable[[PipelineEvent], None] | None = None,
    runs_dir: Path,
    figures_dir: Path,
    sandbox_image: str = "math-variant-sandbox:test",
    forbidden_context: dict[str, str] | None = None,
    scope_profile: str | None = None,
    scope_section: str | None = None,
    critic_scope_section: str | None = None,
    reference_runnable: Runnable[dict[str, str], dict[str, Any]] | None = None,
) -> AgentPipeline:
    """기본 httpx 공급자·에이전트를 묶어 AgentPipeline 을 구성한다."""
    settings = ProviderSettings()
    registry = build_provider_registry(settings)
    schemas = SchemaRegistry()
    register_agent_schemas(schemas)
    resolver = RoleResolver(settings.role_policy(), registry)
    engine = StructuredOutputEngine(
        primary=None, fallback=None, schemas=schemas, on_event=on_event
    )
    engine.role_resolver = resolver

    def _prompt(name: str) -> str:
        return (PROMPTS_DIR / name).read_text(encoding="utf-8")

    sec_planner, sec_critic = _resolve_scope_sections(
        scope_profile=scope_profile,
        scope_section=scope_section,
        critic_scope_section=critic_scope_section,
    )
    runnable = (
        reference_runnable
        if reference_runnable is not None
        else _resolve_reference_runnable()
    )

    return AgentPipeline(
        planner=PlannerAgent(engine, _prompt("planner.md")),
        ideator=IdeatorAgent(engine, _prompt("ideator.md")),
        selector=SelectorAgent(engine, _prompt("selector.md")),
        generator=GeneratorAgent(engine, _prompt("candidate_generator.md")),
        code_reviewer=CodeReviewAgent(engine, _prompt("code_reviewer.md")),
        critic=CriticAgent(engine, _prompt("critic.md")),
        judge=JudgeAgent(engine, _prompt("judge.md")),
        vision=VisionArtist(engine, _prompt("vision.md"), figures_dir),
        sandbox=DockerSandboxProvider(image=sandbox_image),
        blind_solvers=BlindSolver(
            LLMBlindSolver(engine, _prompt("blind_solver.md"), "A"),
            LLMBlindSolver(engine, _prompt("blind_solver.md"), "B"),
            forbidden_context or {},
        ),
        runs_dir=runs_dir,
        ideator_count=ideator_count,
        max_refine=max_refine,
        on_event=on_event,
        scope_section=sec_planner,
        critic_scope_section=sec_critic,
        reference_runnable=runnable,
    )


def build_pipeline(
    *,
    engine: Literal["default", "langchain"] | None = None,
    ideator_count: int = 3,
    max_refine: int = 2,
    on_event: Callable[[PipelineEvent], None] | None = None,
    runs_dir: Path,
    figures_dir: Path,
    sandbox_image: str = "math-variant-sandbox:test",
    forbidden_context: dict[str, str] | None = None,
    scope_profile: str | None = None,
    scope_section: str | None = None,
    critic_scope_section: str | None = None,
    reference_runnable: Runnable[dict[str, str], dict[str, Any]] | None = None,
    enable_style_align: bool | None = None,
) -> PipelineRunnerProtocol:
    """엔진 설정(또는 MATH_VARIANT_PIPELINE_ENGINE 환경변수)에 따라 파이프라인을 생성한다."""
    chosen_engine = engine or os.getenv("MATH_VARIANT_PIPELINE_ENGINE", "default").lower()
    runnable = (
        reference_runnable
        if reference_runnable is not None
        else _resolve_reference_runnable()
    )

    if chosen_engine == "langchain":
        from math_variant.langchain_generator.pipeline import build_langchain_pipeline

        sec_planner, sec_critic = _resolve_scope_sections(
            scope_profile=scope_profile,
            scope_section=scope_section,
            critic_scope_section=critic_scope_section,
        )

        return build_langchain_pipeline(
            ideator_count=ideator_count,
            max_refine=max_refine,
            on_event=on_event,
            runs_dir=runs_dir,
            figures_dir=figures_dir,
            sandbox_image=sandbox_image,
            forbidden_context=forbidden_context,
            scope_section=sec_planner,
            critic_scope_section=sec_critic,
            reference_runnable=runnable,
            enable_style_align=enable_style_align,
        )


    return build_agent_pipeline(
        ideator_count=ideator_count,
        max_refine=max_refine,
        on_event=on_event,
        runs_dir=runs_dir,
        figures_dir=figures_dir,
        sandbox_image=sandbox_image,
        forbidden_context=forbidden_context,
        scope_profile=scope_profile,
        scope_section=scope_section,
        critic_scope_section=critic_scope_section,
        reference_runnable=runnable,
    )

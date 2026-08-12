"""파이프라인 팩토리 — CLI·웹(API)이 공용으로 사용하는 AgentPipeline 구성.

실제 LLM 공급자 호출은 여기서 하지 않고 AgentPipeline.run() 시점에 발생한다.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from math_variant.agents.blind import LLMBlindSolver
from math_variant.agents.code_reviewer import CodeReviewAgent
from math_variant.agents.critic import CriticAgent
from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.ideator import IdeatorAgent
from math_variant.agents.judge import JudgeAgent
from math_variant.agents.pipeline import AgentPipeline
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
from math_variant.sandbox.provider import DockerSandboxProvider
from math_variant.services.blind_solver import BlindSolver

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def build_agent_pipeline(
    *,
    ideator_count: int = 3,
    max_refine: int = 2,
    on_event: Callable[[PipelineEvent], None] | None = None,
    runs_dir: Path,
    figures_dir: Path,
    sandbox_image: str = "math-variant-sandbox:test",
    forbidden_context: dict[str, str] | None = None,
) -> AgentPipeline:
    """설정·공급자·에이전트를 묶어 AgentPipeline 을 구성한다.

    NOTE: `runs_dir` 은 반드시 JOB 단위 고유 디렉터리여야 한다.
    AgentPipeline._write_report 가 `runs_dir/report.json` 에 무조건 쓰므로,
    웹 레이어가 여러 job 을 동시에 실행하면 서로 report.json 을 덮어쓴다.
    CLI 단발 실행은 `Path("runs")` 로 충분하지만, 웹 워커는 실행마다
    per-run 디렉터리를 만들어 넘겨야 한다 (실제 per-job 배선은 Task 8).
    """
    settings = ProviderSettings()
    registry = build_provider_registry(settings)
    schemas = SchemaRegistry()
    register_agent_schemas(schemas)
    resolver = RoleResolver(settings.role_policy(), registry)
    engine = StructuredOutputEngine(primary=None, fallback=None, schemas=schemas, on_event=on_event)
    engine.role_resolver = resolver

    def _prompt(name: str) -> str:
        return (PROMPTS_DIR / name).read_text(encoding="utf-8")

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
    )

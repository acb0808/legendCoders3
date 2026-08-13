"""LangChain 체인을 조합한 문제 생성기 — planner→ideator→generator 순차 실행.

기존 httpx 파이프라인의 에이전트와 동일한 입력 섹션 포맷(`[원문]`, `[문제 구조]`,
`[승인 청사진]`, `[금지 구조 ...]`)을 유지하되, 역할 프롬프트는 체인의 시스템
메시지에 있으므로 human 입력에는 원문·스펙·청사진만 담는다.
원문 분리 원칙은 그대로 지킨다 — 원문 본문은 planner 입력에만 들어간다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.runnables import Runnable
from pydantic import BaseModel, ConfigDict

from math_variant.agents.ideator import build_ideation_brief
from math_variant.agents.schemas import GeneratorOutput, IdeationOutput, PlannerOutput
from math_variant.domain.candidate import CandidateProblem
from math_variant.langchain_generator.chains import build_structured_chain
from math_variant.langchain_generator.settings import build_chat_model, resolve_llm_config

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class GeneratedCandidate(BaseModel):
    """LangChain 파이프라인이 만든 후보 문제와 중간 산출물 묶음."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate: CandidateProblem
    generator_output: GeneratorOutput
    plan: PlannerOutput
    idea: IdeationOutput


def _plan_input(source_text: str, difficulty_target: str) -> str:
    """기획자 human 입력 — 원문과 난이도 목표만 담는다."""
    prompt = f"[원문]\n{source_text}"
    if difficulty_target.strip():
        prompt += f"\n[난이도 목표]\n{difficulty_target}"
    return prompt


def _ideation_input(brief: str, forbidden_structure: list[str]) -> str:
    """발상자 human 입력 — 스펙 브리프와 금지 구조만 담는다 (원문 없음)."""
    prompt = f"[입력]\n{brief}"
    if forbidden_structure:
        prompt += (
            f"\n[금지 구조 (원본 구성 골격, 재사용 금지)]\n- {forbidden_structure}\n"
        )
    return prompt


def _generation_input(
    brief: str,
    blueprint: dict[str, Any],
    forbidden_structure: list[str],
) -> str:
    """생성자 human 입력 — 스펙 브리프·승인 청사진·금지 구조를 담는다."""
    prompt = (
        f"[문제 구조]\n{brief}\n"
        "[승인 청사진]\n"
        f"- 보존: {blueprint.get('preserved_concepts')}\n"
        f"- 변경 차원: {blueprint.get('changed_dimensions')}\n"
        f"- 구성 청사진: {blueprint.get('construction_blueprint')}\n"
    )
    if forbidden_structure:
        prompt += f"[금지 구조 (원본 구성 골격, 재사용 금지)]\n- {forbidden_structure}\n"
    return prompt


class LangChainProblemGenerator:
    """planner·ideator·generator 체인을 순차 실행하는 LangChain 문제 생성기.

    각 체인은 `{"input": "<구조화 입력 문자열>"}` 한 필드만 받는다
    (시스템 프롬프트는 체인 빌더가 역할 md 로 채운다).
    """

    def __init__(
        self,
        planner_chain: Runnable[dict[str, str], PlannerOutput],
        ideator_chain: Runnable[dict[str, str], IdeationOutput],
        generator_chain: Runnable[dict[str, str], GeneratorOutput],
    ) -> None:
        self._planner_chain = planner_chain
        self._ideator_chain = ideator_chain
        self._generator_chain = generator_chain

    def generate(
        self,
        source_text: str,
        difficulty_target: str = "",
        seed: str = "idea-0",
    ) -> GeneratedCandidate:
        """원문 하나를 받아 planner→ideator→generator 순서로 후보 문제를 만든다.

        `seed` 는 후보 식별자(candidate_id)로 사용된다.
        """
        plan = self._planner_chain.invoke({"input": _plan_input(source_text, difficulty_target)})
        brief = build_ideation_brief(
            core_concepts=plan.core_concepts,
            objective=plan.objective,
            answer_type=plan.answer_type,
            domain=plan.domain,
            preservation_goals=plan.preservation_goals,
            strategy=plan.strategy,
        )
        idea = self._ideator_chain.invoke(
            {"input": _ideation_input(brief, plan.forbidden_structure)}
        )
        blueprint: dict[str, Any] = {
            "idea_id": idea.idea_id,
            "title": idea.title,
            "preserved_concepts": idea.preserved_concepts,
            "changed_dimensions": [d.value for d in idea.changed_dimensions],
            "construction_blueprint": idea.construction_blueprint,
        }
        output = self._generator_chain.invoke(
            {"input": _generation_input(brief, blueprint, plan.forbidden_structure)}
        )
        candidate = CandidateProblem(
            candidate_id=seed,
            plan_id=f"plan-{idea.idea_id or 'llm'}",
            problem_text=output.problem_text,
            formalization=output.formalization,
            final_answer_claim=output.final_answer_claim,
            solution_steps=output.solution_steps,
            transformation_evidence=output.transformation_evidence,
        )
        return GeneratedCandidate(
            candidate=candidate,
            generator_output=output,
            plan=plan,
            idea=idea,
        )


def build_langchain_generator(
    *,
    provider: str = "deepseek",
    model: str | None = None,
    prompts_dir: Path = PROMPTS_DIR,
) -> LangChainProblemGenerator:
    """공급자 설정과 역할별 구조화 체인을 묶어 문제 생성기를 구성한다.

    LLM 은 기존 공급자 설정(temperature 미전송)으로 만들고, 시스템 프롬프트는
    기존 `prompts/*.md` 를 재사용한다. 네트워크 호출은 generate() 시점에 발생한다.
    """
    config = resolve_llm_config(provider=provider, model=model)
    llm = build_chat_model(config)

    def _prompt(name: str) -> str:
        return (prompts_dir / name).read_text(encoding="utf-8")

    return LangChainProblemGenerator(
        planner_chain=build_structured_chain(
            llm, system_md=_prompt("planner.md"), output_model=PlannerOutput
        ),
        ideator_chain=build_structured_chain(
            llm, system_md=_prompt("ideator.md"), output_model=IdeationOutput
        ),
        generator_chain=build_structured_chain(
            llm, system_md=_prompt("candidate_generator.md"), output_model=GeneratorOutput
        ),
    )

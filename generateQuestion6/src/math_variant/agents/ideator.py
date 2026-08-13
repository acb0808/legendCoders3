"""발상자 에이전트 — 원문 없이 구조적 변형 아이디어 제안 (T07).

입력에는 원문 본문이 절대 포함되지 않는다. (temperature 는 공급자 특성상 사용하지 않는다)
"""

from __future__ import annotations

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import IdeationOutput, ProductionStrategy
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


def build_ideation_brief(
    *,
    core_concepts: list[str],
    objective: str,
    answer_type: str,
    domain: str,
    preservation_goals: list[str],
    strategy: ProductionStrategy,
) -> str:
    """스펙·전략만 담은 발상 입력 브리프를 만든다 (원문 본문 없음)."""
    return (
        "[문제 구조]\n"
        f"- 핵심 개념: {core_concepts}\n"
        f"- 목표: {objective}\n"
        f"- 답 형태: {answer_type}\n"
        f"- 도메인: {domain}\n"
        f"- 보존 목표: {preservation_goals}\n"
        "[변형 전략]\n"
        f"- 난이도 목표: {strategy.difficulty_target}\n"
        f"- 변형 방향: {strategy.variation_direction}\n"
        f"- 품질 기준: {strategy.quality_criteria}\n"
        f"- 제약: {strategy.constraints}"
    )


class IdeatorAgent:
    """IDEATOR 역할을 호출해 변형 아이디어 하나를 생산한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle

    def ideate(
        self,
        brief: str,
        seed: str,
        forbidden_structure: list[str] | None = None,
        *,
        pattern_section: str = "",
    ) -> IdeationOutput:
        prompt = f"{self.prompt_bundle}\n\n"
        if pattern_section.strip():
            prompt += f"{pattern_section.strip()}\n\n"
        prompt += f"[입력]\n{brief}"
        if forbidden_structure:
            prompt += f"\n[금지 구조 (원본 구성 골격, 재사용 금지)]\n- {forbidden_structure}\n"
        data = request_structured(
            self.engine,
            request_id=f"ideator-{seed}",
            role=RolePolicy.IDEATOR,
            prompt=prompt,
            schema="IdeationOutput",
        )
        return IdeationOutput.model_validate(data)

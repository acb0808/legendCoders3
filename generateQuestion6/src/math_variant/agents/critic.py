"""품질 비평가 — 난이도·참신성·명확성·교육 타당성 평가 (T07)."""

from __future__ import annotations

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import CriticOutput
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


class CriticAgent:
    """CRITIC 역할을 호출해 후보 품질을 평가한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle

    def criticize(
        self, problem_text: str, spec_brief: str, strategy_brief: str, candidate_id: str = "critic"
    ) -> CriticOutput:
        prompt = (
            f"{self.prompt_bundle}\n\n"
            f"[문제 후보]\n{problem_text}\n"
            f"[문제 구조]\n{spec_brief}\n"
            f"[변형 전략]\n{strategy_brief}"
        )
        data = request_structured(
            self.engine,
            request_id=candidate_id,
            role=RolePolicy.CRITIC,
            prompt=prompt,
            schema="CriticOutput",
        )
        return CriticOutput.model_validate(data)

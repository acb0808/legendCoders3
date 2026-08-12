"""기획자 에이전트 — 원문 분석 + 변형 전략 수립 (T07).

원문 본문은 이 에이전트에서만 소비된다. 이후 단계에는 PlannerOutput(스펙·전략)만 전달한다.
"""

from __future__ import annotations

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import PlannerOutput
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


class PlannerAgent:
    """PLANNER 역할을 호출해 원문 스펙·전략을 추출한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle

    def plan(self, source_text: str) -> PlannerOutput:
        prompt = f"{self.prompt_bundle}\n\n[원문]\n{source_text}"
        data = request_structured(
            self.engine,
            request_id="planner",
            role=RolePolicy.PLANNER,
            prompt=prompt,
            schema="PlannerOutput",
        )
        return PlannerOutput.model_validate(data)

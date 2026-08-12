"""선별자 에이전트 — 발상 아이디어 채택 (T07)."""

from __future__ import annotations

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import IdeationOutput, SelectionOutput
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


class SelectorAgent:
    """SELECTOR 역할을 호출해 채택 아이디어를 결정한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle

    def select(self, ideas: list[IdeationOutput], strategy_brief: str) -> SelectionOutput:
        listing = "\n".join(f"- {i.idea_id}: {i.title} | {i.construction_blueprint}" for i in ideas)
        prompt = (
            f"{self.prompt_bundle}\n\n[변형 전략]\n{strategy_brief}\n\n[아이디어 목록]\n{listing}"
        )
        data = request_structured(
            self.engine,
            request_id="selector",
            role=RolePolicy.SELECTOR,
            prompt=prompt,
            schema="SelectionOutput",
        )
        return SelectionOutput.model_validate(data)

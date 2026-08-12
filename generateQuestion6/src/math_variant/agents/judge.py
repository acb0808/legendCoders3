"""최종 집계자 — 검증·합의·품질 종합 순위화 (T07)."""

from __future__ import annotations

import json
from typing import Any

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import JudgeOutput
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


class JudgeAgent:
    """JUDGE 역할을 호출해 후보 랭킹을 산출한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle

    def judge(self, entries: list[dict[str, Any]], run_id: str = "judge") -> JudgeOutput:
        prompt = (
            f"{self.prompt_bundle}\n\n"
            f"[후보 검증 결과]\n{json.dumps(entries, ensure_ascii=False, indent=2)}"
        )
        data = request_structured(
            self.engine,
            request_id=run_id,
            role=RolePolicy.JUDGE,
            prompt=prompt,
            schema="JudgeOutput",
        )
        return JudgeOutput.model_validate(data)

"""검증 스크립트 심사자 — 위험성·정합성 평가 (T07)."""

from __future__ import annotations

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import CodeReviewOutput
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


class CodeReviewAgent:
    """CODE_REVIEWER 역할을 호출해 검증 스크립트를 심사한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle

    def review(
        self, verification_script: str, problem_text: str, claimed_answer: str
    ) -> CodeReviewOutput:
        prompt = (
            f"{self.prompt_bundle}\n\n"
            f"[문제 본문]\n{problem_text}\n"
            f"[주장 답]\n{claimed_answer}\n"
            f"[검증 스크립트]\n```python\n{verification_script}\n```"
        )
        data = request_structured(
            self.engine,
            request_id="code-review",
            role=RolePolicy.CODE_REVIEWER,
            prompt=prompt,
            schema="CodeReviewOutput",
        )
        return CodeReviewOutput.model_validate(data)

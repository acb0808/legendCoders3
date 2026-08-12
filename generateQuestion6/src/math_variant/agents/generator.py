"""생성자 에이전트 — 청사진·스펙만으로 문제 + 검증 스크립트 생성 (T07)."""

from __future__ import annotations

from typing import Any

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import GeneratorOutput
from math_variant.domain.candidate import CandidateProblem
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


class GeneratorAgent:
    """GENERATOR 역할을 호출해 후보 문제와 검증 스크립트를 생산한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle
        self._last_prompt = ""

    def generate(
        self,
        candidate_id: str,
        blueprint: dict[str, Any],
        brief: str,
        feedback: str = "",
    ) -> tuple[CandidateProblem, GeneratorOutput]:
        self._last_prompt = self._build_prompt(blueprint, brief, feedback)
        data = request_structured(
            self.engine,
            request_id=candidate_id,
            role=RolePolicy.GENERATOR,
            prompt=self._last_prompt,
            schema="GeneratorOutput",
        )
        output = GeneratorOutput.model_validate(data)
        candidate = CandidateProblem(
            candidate_id=candidate_id,
            plan_id=f"plan-{blueprint.get('idea_id') or 'llm'}",
            problem_text=output.problem_text,
            formalization=output.formalization,
            final_answer_claim=output.final_answer_claim,
            solution_steps=output.solution_steps,
            transformation_evidence=output.transformation_evidence,
        )
        return candidate, output

    def _build_prompt(self, blueprint: dict[str, Any], brief: str, feedback: str) -> str:
        prompt = (
            f"{self.prompt_bundle}\n\n"
            f"[문제 구조]\n{brief}\n"
            f"[승인 청사진]\n"
            f"- 보존: {blueprint.get('preserved_concepts')}\n"
            f"- 변경 차원: {blueprint.get('changed_dimensions')}\n"
            f"- 구성 청사진: {blueprint.get('construction_blueprint')}\n"
        )
        if feedback.strip():
            prompt += f"[수정 지시]\n{feedback}\n"
        return prompt

"""블라인드 풀이 LLM 어댑터 — BlindSolver 계약(문제 본문만 입력)을 구현한다 (T07)."""

from __future__ import annotations

from math_variant.agents._common import request_structured
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine
from math_variant.services.blind_solver import BlindSolution


class LLMBlindSolver:
    """BLIND_SOLVER 역할을 호출해 후보 문제를 독립 풀이한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str, solver_id: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle
        self.solver_id = solver_id

    def solve(self, problem_text: str) -> BlindSolution:
        prompt = f"{self.prompt_bundle}\n\n[문제 본문]\n{problem_text}"
        data = request_structured(
            self.engine,
            request_id=f"blind-{self.solver_id}",
            role=RolePolicy.BLIND_SOLVER,
            prompt=prompt,
            schema="BlindSolution",
        )
        return BlindSolution.model_validate({**data, "solver_id": self.solver_id})

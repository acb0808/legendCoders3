"""결정론적 변형 엔진 — 승인 계획을 "수학적 상황" 단위로 실현한다.

단순 숫자 치환·실생활 껍데기·기계적 절차(완전제곱식)가 아니라,
핵심 개념(원과 직선의 위치 관계)은 유지하되 상황 자체를 바꾼다:
- 접선(접점 1개) 상황 → 직선이 원과 두 점에서 만나는 할선 상황 (V1)
- 좌표·방정식이 주어져 접선을 구하는 문제 → 원 내부 이동 거리로 중심을 구하는 문제 (V2)

학생이 문제를 보는 순간이 아니라 풀이 중간에 "원과 직선의 위치 관계"임을
깨닫게 하는 것이 목표다. 생성 답은 검증 전 주장이며 BaselineSolver 로 고정 검증한다.
"""

from __future__ import annotations

from math_variant.domain.candidate import CandidateProblem, Formalization, SolutionStepClaim
from math_variant.domain.problem import ProblemSpec
from math_variant.domain.scope import ScopeProfile
from math_variant.domain.transformation import TransformationPlan


class VariationEngine:
    """계획의 변경 차원을 지원 도메인 문항으로 결정론적으로 실현한다."""

    def __init__(self, scope: ScopeProfile) -> None:
        self.scope = scope

    def generate(self, spec: ProblemSpec, plan: TransformationPlan) -> CandidateProblem:
        """원·직선(접선) 원문에서 기본 변형(할선 상황)을 하나 생성한다."""
        return self._secant_variation(spec, plan)

    def generate_variants(
        self, spec: ProblemSpec, plan: TransformationPlan
    ) -> list[CandidateProblem]:
        """여러 상황 변형을 생성한다: 할선(두 점에서 만남) + 원 내부 걷기로 중심 구하기."""
        return [
            self._secant_variation(spec, plan),
            self._center_walk_variation(spec, plan),
        ]

    # --- V1: 접선(접점 1개) → 할선(두 점에서 만남) 상황 ---
    def _secant_variation(self, spec: ProblemSpec, plan: TransformationPlan) -> CandidateProblem:
        # 원 x^2+y^2=5, 직선 y = 2x + k 가 두 점에서 만나도록 → 판별식 D>0 → -5 < k < 5
        r2 = 5
        slope = 2
        problem_text = (
            f"원 x^2 + y^2 = {r2} 에 대하여 직선 y = {slope}x + k 가 서로 다른 두 점에서 "
            "만나도록 하는 실수 k의 범위를 구하고, 그 과정을 서술하시오."
        )
        answer = "-5 < k < 5"
        steps = [
            SolutionStepClaim(
                step_id="s1",
                statement=(
                    f"직선 y = {slope}x + k 를 원 x^2 + y^2 = {r2} 에 대입하면 "
                    f"x^2 + ({slope}x + k)^2 = {r2}, 즉 "
                    f"({slope * slope + 1})x^2 + {2 * slope}kx + (k^2 - {r2}) = 0 이다."
                ),
            ),
            SolutionStepClaim(
                step_id="s2",
                statement=(
                    "직선이 원과 서로 다른 두 점에서 만나려면 이 이차방정식이 "
                    "서로 다른 두 실근을 가져야 하므로 판별식 D > 0 이어야 한다."
                ),
            ),
            SolutionStepClaim(
                step_id="s3",
                statement=(
                    f"D = ({2 * slope}k)^2 - 4({slope * slope + 1})(k^2 - {r2}) = "
                    f"{4 * (slope * slope + 1) * r2} - 4k^2"
                ),
            ),
            SolutionStepClaim(
                step_id="s4",
                statement=(f"D > 0 에서 k^2 < {r2 * (slope * slope + 1)}, 즉 -5 < k < 5 이다."),
            ),
        ]
        evidence = [
            {
                "dimension": "objective",
                "description": "접선의 방정식 → 두 점에서 만나도록 하는 k의 범위 (질문 대상 역전)",
            },
            {
                "dimension": "condition_topology",
                "description": "접점 1개(접선) 상황 → 교점 2개(할선) 상황으로 변경",
            },
            {
                "dimension": "solution_route",
                "description": "거리 = 반지름 → 판별식 D > 0 경로로 유도",
            },
            {"dimension": "data_domain", "description": "원·직선 계수 값 변경"},
        ]
        return self._candidate(spec, plan, problem_text, answer, steps, evidence)

    # --- V2: 원 내부 걷기로 중심 구하기 (관점 역전) ---
    def _center_walk_variation(
        self, spec: ProblemSpec, plan: TransformationPlan
    ) -> CandidateProblem:
        r = 5
        near = 4
        total = 10
        pc = r - near
        problem_text = (
            f"반지름이 {r}인 원이 있다. 원 내부의 점 P에서 직선으로 걸어 원과 처음 만날 "
            f"때까지 걸은 거리가 {near}이고, 계속 같은 방향으로 걸어 원의 반대편에 "
            f"도달하기까지 총 걸은 거리가 {total}이다. 점 P에서 원의 중심까지의 거리를 "
            "구하고, 그 과정을 서술하시오."
        )
        answer = f"{pc:g}"
        steps = [
            SolutionStepClaim(
                step_id="s1",
                statement=(
                    f"직선으로 원을 가로지른 총 거리 {total} 는 지름과 같으므로 "
                    f"반지름 {r} 와 일치한다."
                ),
            ),
            SolutionStepClaim(
                step_id="s2",
                statement=(
                    f"점 P에서 원과 처음 만나는 점까지 걸은 거리는 {near} 이므로, "
                    "P 는 중심에서 처음 만나는 점 쪽으로 떨어져 있다."
                ),
            ),
            SolutionStepClaim(
                step_id="s3",
                statement=(
                    f"중심과 P 는 처음 만나는 점과 같은 반지름 위에 있으므로 "
                    f"PC = r - PA = {r} - {near} = {pc} 이다."
                ),
            ),
        ]
        evidence = [
            {
                "dimension": "objective",
                "description": "접선의 방정식 → 원의 중심까지의 거리 (관점 역전)",
            },
            {
                "dimension": "condition_topology",
                "description": "좌표·방정식이 주어지는 문제 → 도형 내부 이동 거리만으로 결정",
            },
            {
                "dimension": "solution_route",
                "description": "거리 공식 → 지름·반지름의 선분 추론으로 해결",
            },
            {"dimension": "data_domain", "description": "반지름·걸은 거리 값 변경"},
        ]
        return self._candidate(spec, plan, problem_text, answer, steps, evidence)

    # --- 후보 조립 ---
    def _candidate(
        self,
        spec: ProblemSpec,
        plan: TransformationPlan,
        problem_text: str,
        answer: str,
        steps: list[SolutionStepClaim],
        evidence: list[dict[str, str]],
    ) -> CandidateProblem:
        return CandidateProblem(
            candidate_id="cand-demo-1",
            plan_id=plan.plan_id,
            problem_text=problem_text,
            formalization=Formalization(
                symbols=["x", "y", "k"],
                constraints=[],
                goal=spec.objective.natural_language,
            ),
            final_answer_claim=answer,
            solution_steps=steps,
            transformation_evidence=evidence,
        )

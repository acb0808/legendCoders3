"""TransformationPlan — 보존 요소·변형 차원·구성 청사진·검증 계약.

하드 게이트 기준(문서 03 §6):
- 최소 변형 차원 수 충족 (4개 이상)
- 단순 숫자·변수 치환 패턴 아님 → 구조적 변경 2개 이상
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MIN_CHANGE_DIMENSIONS = 4
MIN_STRUCTURAL_CHANGES = 2

PlanFailureCode = Literal[
    "PLAN_CHANGE_DIMENSION_SHORTAGE",
    "PLAN_STRUCTURAL_CHANGE_SHORTAGE",
]


class Dimension(StrEnum):
    """변형 차원 (변형 계획이 바꿀 수 있는 축)."""

    CONTEXT = "context"  # 표면: 상황·맥락
    REPRESENTATION = "representation"  # 표면: 표현 방식
    DATA_DOMAIN = "data_domain"  # 표면: 데이터·숫자 영역
    OBJECTIVE = "objective"  # 구조: 질문 방향
    CONDITION_TOPOLOGY = "condition_topology"  # 구조: 조건 구조
    CONDITION_ORDER = "condition_order"  # 구조: 조건 순서
    AUXILIARY_CONSTRUCTION = "auxiliary_construction"  # 구조: 보조 구성
    SOLUTION_ROUTE = "solution_route"  # 구조: 풀이 경로

    @property
    def is_structural(self) -> bool:
        return self in {
            Dimension.OBJECTIVE,
            Dimension.CONDITION_TOPOLOGY,
            Dimension.CONDITION_ORDER,
            Dimension.AUXILIARY_CONSTRUCTION,
            Dimension.SOLUTION_ROUTE,
        }


class PlanValidationFailure(BaseModel):
    """계획 검증 실패 (구조화된 코드와 감사 로그로 남는다)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: PlanFailureCode
    message: str


class VerificationContract(BaseModel):
    """계획이 약속하는 검증 계약."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    critical_checks: list[str] = Field(default_factory=list)
    fixed_verifier_recipes: list[str] = Field(default_factory=list)
    required_blind_solvers: int = Field(default=0, ge=0)
    counterexample_required: bool = False


class TransformationPlan(BaseModel):
    """승인된 계획: 무엇을 보존하고 어떤 차원을 어떻게 바꿀 것인가."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str
    preserved_concepts: list[str] = Field(min_length=1)
    changed_dimensions: list[Dimension]
    change_description: list[str] = Field(min_length=1)
    rule_ids: list[str] = Field(min_length=1)
    construction_blueprint: str = Field(min_length=1)
    expected_solution_graph_ref: str | None = None
    verification_contract: VerificationContract = Field(default_factory=VerificationContract)
    prohibited_patterns: list[str] = Field(default_factory=list)

    @property
    def structural_change_count(self) -> int:
        return sum(1 for d in self.changed_dimensions if d.is_structural)


def validate_plan(plan: TransformationPlan) -> list[PlanValidationFailure]:
    """계획 불변식을 결정론적으로 검사한다."""
    failures: list[PlanValidationFailure] = []
    unique_dimensions = set(plan.changed_dimensions)

    if len(unique_dimensions) < MIN_CHANGE_DIMENSIONS:
        failures.append(
            PlanValidationFailure(
                code="PLAN_CHANGE_DIMENSION_SHORTAGE",
                message=(
                    f"변형 차원이 {MIN_CHANGE_DIMENSIONS}개 미만이다 "
                    f"(현재 {len(unique_dimensions)}개)"
                ),
            )
        )

    if plan.structural_change_count < MIN_STRUCTURAL_CHANGES:
        failures.append(
            PlanValidationFailure(
                code="PLAN_STRUCTURAL_CHANGE_SHORTAGE",
                message=(
                    f"구조적 변경이 {MIN_STRUCTURAL_CHANGES}개 미만이다 "
                    f"(현재 {plan.structural_change_count}개) — 단순 숫자·표현 치환 패턴"
                ),
            )
        )

    return failures

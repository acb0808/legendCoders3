"""다중 에이전트 응답 스키마 (T07).

모든 스키마는 extra="forbid" 로 LLM 응답의 추가 필드를 거부한다.
원문 본문은 PlannerOutput 에만 허용하고, IDEATOR/SELECTOR/GENERATOR 의
입력에는 원문 전문이 절대 포함되지 않는다 (원문 분리 원칙).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from math_variant.domain.candidate import Formalization, SolutionStepClaim
from math_variant.domain.transformation import Dimension
from math_variant.providers.registry import SchemaRegistry
from math_variant.services.blind_solver import BlindSolution


class ProductionStrategy(BaseModel):
    """기획 단계에서 수립한 변형 전략 (원문 본문 없이 다음 단계로 전달된다)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    difficulty_target: str = Field(min_length=1)
    preservation_goals: list[str] = Field(min_length=1)
    variation_direction: list[str] = Field(min_length=1)
    quality_criteria: list[str] = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    """기획자 출력 — 원문 분석 + 변형 전략."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    core_concepts: list[str] = Field(min_length=1)
    auxiliary_concepts: list[str] = Field(default_factory=list)
    objective: str = Field(min_length=1)
    answer_type: str
    domain: str
    preservation_goals: list[str] = Field(min_length=1)
    strategy: ProductionStrategy
    unresolved_assumptions: list[str] = Field(default_factory=list)


class IdeationOutput(BaseModel):
    """발상자 출력 — 원문 없이 하나의 구조적 변형 아이디어."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    idea_id: str
    title: str = Field(min_length=1)
    preserved_concepts: list[str] = Field(min_length=1)
    changed_dimensions: list[Dimension] = Field(min_length=1)
    change_description: list[str] = Field(min_length=1)
    construction_blueprint: str = Field(min_length=1)
    figure_required: bool = False
    figure_notes: str = Field(default="")


class SelectionOutput(BaseModel):
    """선별자 출력 — 발상 아이디어 중 채택 목록."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    adopted_ideas: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class GeneratorOutput(BaseModel):
    """생성자 출력 — CandidateProblem + 검증 스크립트 + 도형 필요 여부."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    problem_text: str = Field(min_length=1)
    formalization: Formalization
    final_answer_claim: str = Field(min_length=1)
    solution_steps: list[SolutionStepClaim] = Field(default_factory=list)
    transformation_evidence: list[dict[str, Any]] = Field(default_factory=list)
    verification_script: str = Field(min_length=1)
    needs_figure: bool = False
    figure_notes: str = Field(default="")


class CodeReviewOutput(BaseModel):
    """검증 스크립트 심사자 출력."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    verdict: Literal["APPROVE", "REVISE", "REJECT"]
    safe: bool
    test_consistent: bool
    risk_notes: list[str] = Field(default_factory=list)
    feedback: str = Field(default="")

    @property
    def approves(self) -> bool:
        return self.verdict == "APPROVE"


class CriticOutput(BaseModel):
    """품질 비평가 출력."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    score: float = Field(ge=0, le=10)
    difficulty_estimate: str = Field(min_length=1)
    criteria_scores: dict[str, float] = Field(default_factory=dict)
    comments: list[str] = Field(default_factory=list)
    recommendation: Literal["PASS", "REVISE", "REJECT"] = "PASS"


class JudgeOutput(BaseModel):
    """최종 집계 출력 — 랭킹."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ranking: list[dict[str, Any]] = Field(min_length=1)
    summary: str = Field(default="")


class VisionOutput(BaseModel):
    """도형 렌더러 출력 — TikZ 코드."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tikz_code: str = Field(min_length=1)
    caption: str = Field(default="")


def register_agent_schemas(registry: SchemaRegistry) -> None:
    """에이전트 응답 스키마를 레지스트리에 등록한다."""
    for model in (
        PlannerOutput,
        IdeationOutput,
        SelectionOutput,
        GeneratorOutput,
        CodeReviewOutput,
        CriticOutput,
        JudgeOutput,
        VisionOutput,
    ):
        registry.register(model)
    registry.register(BlindSolution)

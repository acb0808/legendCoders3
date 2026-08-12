"""ProblemSpec — 원문 분석 결과를 고정하는 도메인 계약."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from math_variant.domain.scope import AnswerType


class MathStatement(BaseModel):
    """수학 진술 하나 (자연어 + 기계 형식화 + 정의역)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    natural_language: str
    sympy_expr: str | None = None
    domain: str | None = None


class ProblemSpec(BaseModel):
    """정규화 원문에서 추출된 문제 구조.

    원칙: 분석기가 확정하지 못한 가정은 `unresolved_assumptions`로 반환하고
    자동 생성 경로를 막는다. (`T02.4-GT4`)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    spec_id: str
    source_text: str = Field(min_length=1)
    curriculum_version: str
    exam_scope: list[str]
    core_concepts: list[str] = Field(default_factory=list)
    auxiliary_concepts: list[str] = Field(default_factory=list)
    givens: list[MathStatement] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    objective: MathStatement
    answer_type: AnswerType
    explicit_assumptions: list[str] = Field(default_factory=list)
    implicit_domain: list[str] = Field(default_factory=list)
    expected_methods: list[str] = Field(default_factory=list)
    forbidden_knowledge: list[str] = Field(default_factory=list)
    unresolved_assumptions: list[str] = Field(default_factory=list)

    @property
    def has_unresolved_assumptions(self) -> bool:
        """확정하지 못한 가정이 있으면 자동 생성 경로를 막는다."""
        return bool(self.unresolved_assumptions)

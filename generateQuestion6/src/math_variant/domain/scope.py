"""시험 범위 프로파일 (ScopeProfile) — 실행마다 고정되는 범위 설정.

기술 보고서(문서 03)의 지침: 공통수학2 실제 범위는 학교별로 다르므로 `exam_scope`를
필수 설정값으로 두고 허용 단원·성취기준·선수지식·금지 개념을 실행마다 고정한다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AnswerType = Literal[
    "integer",
    "rational",
    "real",
    "expression",
    "set",
    "interval",
    "coordinate",
    "proof",
    "multi_part",
    "angle",
    "length",
    "area",
]


class ScopeProfile(BaseModel):
    """허용 단원·성취기준·개념·답 형태·검증 지원 범위."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: str
    school_name: str
    exam_scope: list[str] = Field(min_length=1)
    curriculum_version: str = "2022 개정"
    allowed_units: list[str] = Field(min_length=1)
    achievement_criteria: list[str] = Field(default_factory=list)
    concept_vocabulary: list[str] = Field(min_length=1)
    forbidden_concepts: list[str] = Field(default_factory=list)
    allowed_answer_types: list[AnswerType] = Field(min_length=1)
    verification_support: list[str] = Field(
        default_factory=lambda: ["sympy", "numeric", "blind_solver"]
    )

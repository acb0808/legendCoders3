"""참조 자산 계층 데이터 모델 (M2).

기출 출제 패턴, 조건 표현 관례, 해설 스타일, 교육과정 범위, 지식체계 개념을
불변(frozen) Pydantic 모델로 정의한다.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExamPatternCard(BaseModel):
    """기출 출제 패턴 요약 카드."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic_id: str
    unit: str
    pattern: str
    wording: str
    condition_style: list[str] = Field(default_factory=list)
    example_abstract: str
    difficulty_zone: str = "중"
    source_count: int = 1
    sources: list[str] = Field(default_factory=list)


class ConditionPhrasing(BaseModel):
    """토픽별 조건 표현 관례 및 발문 패턴."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic_id: str
    unit: str
    patterns: list[str] = Field(default_factory=list)
    wording_conventions: list[str] = Field(default_factory=list)


class SolutionStyle(BaseModel):
    """단원별 표준 해설 서술 스타일 가이드."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit: str
    open: str
    transform_order: list[str] = Field(default_factory=list)
    justification_vocab: list[str] = Field(default_factory=list)
    close: str
    sample_step: str = ""


class CurriculumScope(BaseModel):
    """교육과정 허용 및 금지 범위 프로파일."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic_ids: list[str] = Field(default_factory=list)
    allowed_concepts: list[str] = Field(default_factory=list)
    disallowed_concepts: list[str] = Field(default_factory=list)
    skill_descriptions: dict[str, str] = Field(default_factory=dict)


class KnowledgeConcept(BaseModel):
    """지식체계 상의 수학 개념 항목."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int | None
    name: str
    semester: str = ""
    description: str = ""

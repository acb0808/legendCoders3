"""수학 지식체계 인덱스 및 skill_id 매핑 모듈 (M2).

scope_profile.json 에 캐시된 지식체계 인덱스를 로드하고,
풀이 단계(SolutionStepClaim)에 표준 skill_id 를 순수 규칙 기반으로 부여한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from math_variant.domain.candidate import SolutionStepClaim
from math_variant.reference.models import KnowledgeConcept

DEFAULT_PROFILE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "scope_profile.json"
)


class KnowledgeIndex(BaseModel):
    """지식체계 개념 인덱스 모델."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    skills: dict[str, KnowledgeConcept] = Field(default_factory=dict)


def load_knowledge_index(path: Path | None = None) -> KnowledgeIndex:
    """scope_profile.json 로드 후 KnowledgeIndex 객체를 생성한다."""
    target_path = path or DEFAULT_PROFILE_PATH
    if not target_path.exists():
        return KnowledgeIndex(skills={})

    with open(target_path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    skill_index_raw = data.get("skill_index", {})
    skills: dict[str, KnowledgeConcept] = {}
    if isinstance(skill_index_raw, dict):
        for name, item in skill_index_raw.items():
            if isinstance(item, dict):
                skills[name] = KnowledgeConcept(
                    id=item.get("id"),
                    name=name,
                    semester=str(item.get("semester", "")),
                    description=str(item.get("description", "")),
                )

    return KnowledgeIndex(skills=skills)


def assign_skill_ids(
    solution_steps: list[SolutionStepClaim],
    concepts: list[str],
    knowledge_index: KnowledgeIndex | None = None,
) -> list[dict[str, Any]]:
    """각 풀이 단계에 해당하는 수학 지식체계 skill_id 를 매핑하여 증거 레코드를 생성한다."""
    index = knowledge_index or load_knowledge_index()
    evidences: list[dict[str, Any]] = []

    for step in solution_steps:
        step_text = f"{step.statement} {step.justification}"
        matched_concept: KnowledgeConcept | None = None

        # 1. 플래너 core_concepts 와 매칭 시도
        for c_name in concepts:
            if c_name in index.skills and c_name in step_text:
                matched_concept = index.skills[c_name]
                break

        # 2. 전체 지식체계 인덱스 키워드 매칭
        if not matched_concept:
            for name, concept in index.skills.items():
                if name in step_text:
                    matched_concept = concept
                    break

        if matched_concept and matched_concept.id is not None:
            evidences.append(
                {
                    "dimension": "skill_mapping",
                    "step_id": step.step_id,
                    "skill_id": str(matched_concept.id),
                    "concept_name": matched_concept.name,
                }
            )
        else:
            evidences.append(
                {
                    "dimension": "skill_mapping",
                    "step_id": step.step_id,
                    "skill_id": None,
                    "reason": "no_match",
                }
            )

    return evidences

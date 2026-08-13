"""교육과정 범위 관리 및 스코프 빌더 (M2).

scope_profile.json 로드 및 환경변수(MATH_VARIANT_SCOPE), 설정 스위치에 따라
공통수학2(C08) 세부 범위(도형, 집합, 함수)를 제어한다.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from math_variant.reference.models import CurriculumScope

DEFAULT_PROFILE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "scope_profile.json"
)


def build_scope(
    include_sets: bool = False,
    include_functions: bool = False,
    profile_path: Path | None = None,
) -> CurriculumScope:
    """설정 스위치에 따라 허용/금지 개념 목록을 포함하는 CurriculumScope 를 생성한다."""
    path = profile_path or DEFAULT_PROFILE_PATH
    if not path.exists():
        # 기본 하드코딩 도형 범위 폴백
        return CurriculumScope(
            topic_ids=["C08-01-01-01", "C08-01-02-01", "C08-01-03-01", "C08-01-04-01"],
            allowed_concepts=["평면좌표", "직선의 방정식", "원의 방정식", "도형의 이동"],
            disallowed_concepts=["지수", "로그", "수열", "삼각함수", "미분계수", "적분"],
            skill_descriptions={},
        )

    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    all_topic_ids: list[str] = list(data.get("topic_ids", []))
    skill_desc: dict[str, str] = dict(data.get("skill_descriptions", {}))
    base_disallowed: list[str] = list(data.get("disallowed_concepts", []))

    selected_topics: list[str] = []
    allowed_concepts: list[str] = []
    dynamic_disallowed: list[str] = list(base_disallowed)

    for tid in all_topic_ids:
        concept_name = skill_desc.get(tid, "")
        if tid.startswith("C08-01"):  # 도형의 방정식 (항상 포함)
            selected_topics.append(tid)
            if concept_name and concept_name not in allowed_concepts:
                allowed_concepts.append(concept_name)
        elif tid.startswith("C08-02"):  # 집합과 명제
            if include_sets:
                selected_topics.append(tid)
                if concept_name and concept_name not in allowed_concepts:
                    allowed_concepts.append(concept_name)
            else:
                if concept_name and concept_name not in dynamic_disallowed:
                    dynamic_disallowed.append(concept_name)
        elif tid.startswith("C08-03"):  # 함수
            if include_functions:
                selected_topics.append(tid)
                if concept_name and concept_name not in allowed_concepts:
                    allowed_concepts.append(concept_name)
            else:
                if concept_name and concept_name not in dynamic_disallowed:
                    dynamic_disallowed.append(concept_name)

    return CurriculumScope(
        topic_ids=selected_topics,
        allowed_concepts=sorted(allowed_concepts),
        disallowed_concepts=sorted(dynamic_disallowed),
        skill_descriptions=skill_desc,
    )


def load_scope_from_env(profile_path: Path | None = None) -> CurriculumScope | None:
    """환경변수 MATH_VARIANT_SCOPE 에 따라 CurriculumScope 를 로드한다."""
    scope_env = os.environ.get("MATH_VARIANT_SCOPE", "geometry").strip().lower()
    if scope_env == "off":
        return None
    if scope_env == "with_sets":
        return build_scope(include_sets=True, include_functions=False, profile_path=profile_path)
    if scope_env == "full":
        return build_scope(include_sets=True, include_functions=True, profile_path=profile_path)
    # 기본: geometry
    return build_scope(include_sets=False, include_functions=False, profile_path=profile_path)

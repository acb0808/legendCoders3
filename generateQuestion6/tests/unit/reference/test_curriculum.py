"""단위 테스트 — 교육과정 범위 및 스코프 로더 (M2 TDD).

CurriculumScope 모델, build_scope() 스위치, load_scope_from_env() 환경변수 해석을 검증한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from math_variant.reference.curriculum import (
    build_scope,
    load_scope_from_env,
)
from math_variant.reference.models import CurriculumScope


@pytest.fixture
def mock_scope_profile_file(tmp_path: Path) -> Path:
    """합성 scope_profile.json 파일 생성."""
    profile_data = {
        "topic_ids": [
            "C08-01-01-01",
            "C08-01-02-01",
            "C08-01-03-01",
            "C08-02-01-01",
            "C08-03-01-01",
        ],
        "allowed_concepts": [
            "두 점 사이의 거리",
            "직선의 방정식",
            "원의 방정식의 표준형",
            "집합의 개념",
            "함수의 정의",
        ],
        "disallowed_concepts": ["지수", "로그", "수열", "미분계수"],
        "skill_descriptions": {
            "C08-01-01-01": "두 점 사이의 거리",
            "C08-01-02-01": "직선의 방정식",
            "C08-01-03-01": "원의 방정식의 표준형",
            "C08-02-01-01": "집합의 개념",
            "C08-03-01-01": "함수의 정의",
        },
        "skill_index": {
            "원의 방정식의 표준형": {"id": 3142, "semester": "고등-공통수학2", "description": "원"},
        },
    }
    p = tmp_path / "scope_profile.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, ensure_ascii=False)
    return p


def test_build_scope_switches(mock_scope_profile_file: Path) -> None:
    """build_scope가 도형/집합/함수 포함 스위치에 따라 적절한 범위를 구성하는지 검증."""
    # 1. 기본: 도형의 방정식만 (C08-01)
    scope_geo = build_scope(
        include_sets=False,
        include_functions=False,
        profile_path=mock_scope_profile_file,
    )
    assert isinstance(scope_geo, CurriculumScope)
    assert "C08-01-01-01" in scope_geo.topic_ids
    assert "C08-02-01-01" not in scope_geo.topic_ids
    assert "C08-03-01-01" not in scope_geo.topic_ids
    assert "두 점 사이의 거리" in scope_geo.allowed_concepts
    assert "집합의 개념" in scope_geo.disallowed_concepts

    # 2. 집합 포함
    scope_sets = build_scope(
        include_sets=True,
        include_functions=False,
        profile_path=mock_scope_profile_file,
    )
    assert "C08-02-01-01" in scope_sets.topic_ids
    assert "C08-03-01-01" not in scope_sets.topic_ids

    # 3. 전체 포함
    scope_full = build_scope(
        include_sets=True,
        include_functions=True,
        profile_path=mock_scope_profile_file,
    )
    assert "C08-01-01-01" in scope_full.topic_ids
    assert "C08-02-01-01" in scope_full.topic_ids
    assert "C08-03-01-01" in scope_full.topic_ids


def test_load_scope_from_env(
    mock_scope_profile_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MATH_VARIANT_SCOPE 환경변수("geometry", "with_sets", "full", "off") 해석 검증."""
    monkeypatch.setenv("MATH_VARIANT_SCOPE", "with_sets")
    scope = load_scope_from_env(profile_path=mock_scope_profile_file)
    assert scope is not None
    assert "C08-02-01-01" in scope.topic_ids

    monkeypatch.setenv("MATH_VARIANT_SCOPE", "off")
    scope_off = load_scope_from_env(profile_path=mock_scope_profile_file)
    assert scope_off is None

"""단위 테스트 — 지식체계 인덱스 및 skill_id 매핑 (M2 TDD).

load_knowledge_index() 및 assign_skill_ids() 순수 함수의 키워드 매칭과 null 처리를 검증한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from math_variant.domain.candidate import SolutionStepClaim
from math_variant.reference.knowledge_graph import (
    KnowledgeIndex,
    assign_skill_ids,
    load_knowledge_index,
)


@pytest.fixture
def mock_knowledge_profile_file(tmp_path: Path) -> Path:
    """합성 지식체계 인덱스 파일 생성."""
    profile_data = {
        "skill_index": {
            "원의 방정식의 표준형": {
                "id": 3142,
                "semester": "고등-공통수학2",
                "description": "중심과 반지름으로 표현된 원의 방정식",
            },
            "두 점 사이의 거리": {
                "id": 1442,
                "semester": "고등-공통수학2",
                "description": "좌표평면 위의 두 점 사이의 거리",
            },
            "직선의 방정식": {
                "id": 2105,
                "semester": "고등-공통수학2",
                "description": "기울기와 한 점으로 표현된 직선",
            },
        }
    }
    p = tmp_path / "scope_profile.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, ensure_ascii=False)
    return p


def test_load_knowledge_index(mock_knowledge_profile_file: Path) -> None:
    """load_knowledge_index가 scope_profile.json의 skill_index를 로드하는지 검증."""
    index = load_knowledge_index(mock_knowledge_profile_file)
    assert isinstance(index, KnowledgeIndex)
    assert "원의 방정식의 표준형" in index.skills
    assert index.skills["원의 방정식의 표준형"].id == 3142


def test_assign_skill_ids_matches_keywords(mock_knowledge_profile_file: Path) -> None:
    """assign_skill_ids가 풀이 단계 내용과 매칭하여 skill_id 또는 null을 부여하는지 검증."""
    index = load_knowledge_index(mock_knowledge_profile_file)

    steps = [
        SolutionStepClaim(
            step_id="step-1",
            statement="원의 방정식의 표준형 $(x-1)^2 + (y-2)^2 = 4$를 구한다.",
            justification="원의 중심과 반지름 대입",
        ),
        SolutionStepClaim(
            step_id="step-2",
            statement="점 $A$와 점 $B$의 두 점 사이의 거리를 계산한다.",
            justification="거리 공식 적용",
        ),
        SolutionStepClaim(
            step_id="step-3",
            statement="상수 $k$를 최종적으로 구한다.",
            justification="단순 산술 연산",
        ),
    ]

    evidences = assign_skill_ids(
        solution_steps=steps,
        concepts=["원의 방정식", "평면좌표"],
        knowledge_index=index,
    )

    assert len(evidences) == 3

    # step-1 매칭 성공
    e1 = evidences[0]
    assert e1["dimension"] == "skill_mapping"
    assert e1["step_id"] == "step-1"
    assert e1["skill_id"] == "3142"
    assert e1["concept_name"] == "원의 방정식의 표준형"

    # step-2 매칭 성공
    e2 = evidences[1]
    assert e2["step_id"] == "step-2"
    assert e2["skill_id"] == "1442"

    # step-3 매칭 실패 (null 기록)
    e3 = evidences[2]
    assert e3["step_id"] == "step-3"
    assert e3["skill_id"] is None
    assert e3["reason"] == "no_match"

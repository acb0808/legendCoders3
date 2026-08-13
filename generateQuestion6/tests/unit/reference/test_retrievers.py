"""단위 테스트 — 참조 리트리버 3종 (M2 TDD).

ExamPatternRetriever, ConditionStyleRetriever, SolutionStyleRetriever의
BaseRetriever invoke 계약, topic_id 매칭, 부분 일치, 상위 단원 폴백, 빈 결과 처리를 검증한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from math_variant.reference.condition_retriever import ConditionStyleRetriever
from math_variant.reference.exam_retriever import ExamPatternRetriever
from math_variant.reference.style_retriever import SolutionStyleRetriever


@pytest.fixture
def temp_reference_dir(tmp_path: Path) -> Path:
    """합성 참조 데이터 디렉터리 픽스처 생성."""
    # 1. exam patterns jsonl
    exam_card = {
        "topic_id": "C08-01-03-01",
        "unit": "원의 방정식",
        "pattern": "[원의 방정식] 최댓값은?",
        "wording": "최댓값은?",
        "condition_style": ["원 _와 직선 _가 만날 때", "상수 _의 값"],
        "example_abstract": "원 _와 직선 _가 만날 때, 상수 _의 최댓값은?",
        "difficulty_zone": "상",
        "source_count": 5,
        "sources": ["2023_midterm#1", "2023_midterm#2"],
    }
    exam_path = tmp_path / "reference_exam_patterns.jsonl"
    with open(exam_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(exam_card, ensure_ascii=False) + "\n")

    # 2. condition style index json
    condition_data = {
        "C08-01-03-01": {
            "topic_id": "C08-01-03-01",
            "unit": "원의 방정식",
            "condition_phrasings": [
                {"pattern": "원 _와 직선 _가 만날 때", "freq": 10},
                {"pattern": "중심이 _이고 반지름이 _인 원", "freq": 8},
            ],
            "wording_conventions": ["최댓값을 구하시오", "상수 k의 값은?"],
        }
    }
    cond_path = tmp_path / "condition_style_index.json"
    with open(cond_path, "w", encoding="utf-8") as f:
        json.dump(condition_data, f, ensure_ascii=False)

    # 3. solution style guide json
    style_data = {
        "원의 방정식": {
            "unit": "원의 방정식",
            "style": {
                "open": "주어진 원의 방정식을 표준형으로 정리하면",
                "transform_order": [
                    "표준형 변환",
                    "점과 직선 사이의 거리 공식 적용",
                    "부등식 계산",
                ],
                "justification_vocab": ["정리하면", "따라서", "이므로", "대입하면"],
                "close": "따라서 구하는 최댓값은 ~이다.",
                "sample_step": "1단계: 표준형 정리. 2단계: 거리 공식. 3단계: 최댓값 도출",
            },
        }
    }
    style_path = tmp_path / "solution_style_guide.json"
    with open(style_path, "w", encoding="utf-8") as f:
        json.dump(style_data, f, ensure_ascii=False)

    return tmp_path


def test_exam_pattern_retriever_contract_and_fallback(temp_reference_dir: Path) -> None:
    """ExamPatternRetriever가 BaseRetriever 계약을 준수하고 토픽 매칭을 수행하는지 검증."""
    retriever = ExamPatternRetriever(
        index_path=temp_reference_dir / "reference_exam_patterns.jsonl",
        k=3,
    )
    assert isinstance(retriever, BaseRetriever)

    # 1. 완전 일치 (topic_id)
    docs = retriever.invoke("C08-01-03-01,원의 방정식")
    assert len(docs) == 1
    assert isinstance(docs[0], Document)
    assert docs[0].metadata["topic_id"] == "C08-01-03-01"
    assert "최댓값은?" in docs[0].page_content

    # 2. 개념명 부분 일치
    docs2 = retriever.invoke("원")
    assert len(docs2) == 1

    # 3. 상위 단원 폴백 (C08-01)
    docs3 = retriever.invoke("C08-01-01-01")  # 평면좌표 요청 시 C08-01 상위 단원 폴백
    assert len(docs3) == 1

    # 4. 불일치 시 빈 리스트 반환 (예외 없음)
    docs_empty = retriever.invoke("C09-99-99-99,미적분")
    assert docs_empty == []


def test_condition_style_retriever_contract_and_empty(temp_reference_dir: Path) -> None:
    """ConditionStyleRetriever가 BaseRetriever 계약과 빈 결과를 정상 처리하는지 검증."""
    retriever = ConditionStyleRetriever(
        index_path=temp_reference_dir / "condition_style_index.json",
        k=5,
    )
    assert isinstance(retriever, BaseRetriever)

    docs = retriever.invoke("C08-01-03-01")
    assert len(docs) == 1
    assert "원 _와 직선 _가 만날 때" in docs[0].page_content
    assert docs[0].metadata["topic_id"] == "C08-01-03-01"

    docs_empty = retriever.invoke("C09-01-01")
    assert docs_empty == []


def test_solution_style_retriever_contract_and_none(temp_reference_dir: Path) -> None:
    """SolutionStyleRetriever가 단원별 해설 스타일을 Document로 반환하는지 검증."""
    retriever = SolutionStyleRetriever(
        index_path=temp_reference_dir / "solution_style_guide.json",
    )
    assert isinstance(retriever, BaseRetriever)

    docs = retriever.invoke("원의 방정식")
    assert len(docs) == 1
    assert "표준형으로 정리하면" in docs[0].page_content
    assert docs[0].metadata["unit"] == "원의 방정식"

    docs_empty = retriever.invoke("미적분")
    assert docs_empty == []

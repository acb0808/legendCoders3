"""단위 테스트 — 참조 인덱스 추출 빌더 4종 (M1 TDD).

합성 픽스처(시험지, 코퍼스, CSV, 지식체계)를 활용해 순수 변환 함수의
단원 분류, n-gram 정규화, C08 필터링, 지식체계 인덱싱을 검증한다.
"""

from __future__ import annotations

from typing import Any

from scratch.build_condition_style_index import extract_condition_style_index
from scratch.build_exam_patterns import extract_exam_patterns
from scratch.build_scope_profile import extract_scope_profile
from scratch.build_solution_style_guide import extract_solution_style_guide


def test_extract_exam_patterns_classifies_unit_and_normalizes() -> None:
    """시험지 문항에서 단원을 분류하고 수식을 정규화하여 패턴 카드를 생성하는지 검증."""
    sample_exam = [
        {
            "question_number": "1",
            "question_text": (
                "두 점 <eq>A(1, 2)</eq>, <eq>B(4, 6)</eq>에 대하여 "
                "선분 <eq>AB</eq>의 길이를 구하시오."
            ),
            "score": "3.5",
            "images": [],
            "options": [],
        },
        {
            "question_number": "2",
            "question_text": (
                "원 <eq>x^2 + y^2 = 4</eq>와 직선 <eq>y = x + k</eq>가 "
                "만날 때, 상수 <eq>k</eq>의 최댓값은?"
            ),
            "score": "4.2",
            "images": [],
            "options": ["1", "2", "2\\sqrt{2}", "4", "5"],
        },
    ]
    exams_data = [("2023_sample_midterm", sample_exam)]

    cards = extract_exam_patterns(exams_data)
    assert len(cards) >= 2

    # 평면좌표 문항 검증
    plane_cards = [c for c in cards if c["unit"] == "평면좌표"]
    assert len(plane_cards) >= 1
    c1 = plane_cards[0]
    assert c1["topic_id"].startswith("C08-01")
    assert "구하시오" in c1["wording"]
    assert any("두 점" in p for p in c1["condition_style"])
    assert "<eq>" not in c1["example_abstract"] or "_" in c1["example_abstract"]
    assert c1["source_count"] == 1
    assert "2023_sample_midterm#1" in c1["sources"]

    # 원의 방정식 문항 검증
    circle_cards = [c for c in cards if c["unit"] == "원의 방정식"]
    assert len(circle_cards) >= 1
    c2 = circle_cards[0]
    assert "최댓값은?" in c2["wording"] or "값은?" in c2["wording"]


def test_extract_condition_style_index_filters_c08_and_counts_freq() -> None:
    """코퍼스에서 C08 문항만 필터링하고 조건 표현 관례를 집계하는지 검증."""
    corpus_items = [
        {
            "id": "item-1",
            "question_info": [
                {
                    "assigned_topic_id": "C08-01-01-01",
                    "question_unit": "07",
                    "question_topic_name": "두 점 사이의 거리",
                }
            ],
            "OCR_info": [
                {
                    "question_text": (
                        "두 점 $A(1, 2), B(3, 4)$에 대하여 "
                        "선분 $AB$의 길이를 구하시오."
                    )
                }
            ],
        },
        {
            "id": "item-2",
            "question_info": [
                {
                    "assigned_topic_id": "C08-01-01-01",
                    "question_unit": "07",
                    "question_topic_name": "두 점 사이의 거리",
                }
            ],
            "OCR_info": [
                {
                    "question_text": (
                        "두 점 $P(-1, 0), Q(2, 3)$에 대하여 "
                        "선분 $PQ$를 $2:1$로 내분하는 점은?"
                    )
                }
            ],
        },
        {
            "id": "item-3",
            "question_info": [
                {
                    "assigned_topic_id": "C09-01-01-01",  # C09 제외 대상
                    "question_unit": "01",
                    "question_topic_name": "지수",
                }
            ],
            "OCR_info": [{"question_text": "$2^x = 4$일 때 $x$의 값을 구하시오."}],
        },
    ]

    index = extract_condition_style_index(corpus_items, min_freq=1)
    assert "C08-01-01-01" in index
    assert "C09-01-01-01" not in index

    topic_entry = index["C08-01-01-01"]
    assert topic_entry["unit"] == "두 점 사이의 거리" or "평면좌표" in topic_entry["unit"]
    phrasings = topic_entry["condition_phrasings"]
    assert any("두 점" in p["pattern"] for p in phrasings)
    assert len(topic_entry["wording_conventions"]) >= 1


def test_extract_solution_style_guide_extracts_connectors_and_order() -> None:
    """개념서 OCR 텍스트에서 접속어와 서술 순서를 추출하여 스타일 가이드를 만드는지 검증."""
    concept_items = [
        {
            "unit": "원의 방정식",
            "converted_text": (
                "주어진 원의 중심을 구하면 $(1, 2)$이다.\n"
                "정리하면 $x^2 + y^2 = 4$이므로 반지름은 $2$이다.\n"
                "따라서 구하는 값은 $4$이다."
            ),
        },
        {
            "unit": "평면좌표",
            "converted_text": (
                "선분 $AB$의 중점을 $M$이라 하자.\n"
                "즉 점과 직선 사이의 거리 공식에 의하여 $d=3$이다.\n"
                "그러므로 최솟값은 $5$이다."
            ),
        },
    ]

    guide = extract_solution_style_guide(concept_items)
    assert "원의 방정식" in guide
    circle_style = guide["원의 방정식"]["style"]
    assert "open" in circle_style
    assert "transform_order" in circle_style
    assert "justification_vocab" in circle_style
    assert "따라서" in circle_style["close"] or "구하는" in circle_style["close"]
    assert len(circle_style["justification_vocab"]) >= 1


def test_extract_scope_profile_parses_curriculum_and_knowledge() -> None:
    """교육과정 CSV(C08/C09) 및 지식체계 JSON을 파싱하여 허용/금지 토픽을 빌드하는지 검증."""
    csv_content = """Topic_ID,과정(학년),대단원,중단원,소단원(토픽),유형_태그,난이도,비고
C08-01-01-01,공통수학2,도형의 방정식,평면좌표,두 점 사이의 거리,,,
C08-01-03-01,공통수학2,도형의 방정식,원의 방정식,원의 방정식의 표준형,,,
C08-02-01-01,공통수학2,집합과 명제,집합,집합의 개념,,,
C09-01-01-01,수학I,지수함수와 로그함수,지수,거듭제곱과 거듭제곱근,,,
"""
    knowledge_data: dict[str, Any] = {
        "0": {
            "fromConcept": {
                "id": 3142,
                "name": "원의 방정식의 표준형",
                "semester": "고등-공통수학2",
                "description": "중심이 (a, b)이고 반지름이 r인 원의 방정식",
            },
            "toConcept": {
                "id": 1442,
                "name": "두 점 사이의 거리",
                "semester": "고등-공통수학2",
                "description": "두 점 사이의 거리 공식",
            },
        }
    }

    profile = extract_scope_profile(csv_content, knowledge_data)

    assert "C08-01-01-01" in profile["topic_ids"]
    assert "C08-01-03-01" in profile["topic_ids"]
    assert "C09-01-01-01" not in profile["topic_ids"]

    assert "두 점 사이의 거리" in profile["allowed_concepts"]
    assert "원의 방정식의 표준형" in profile["allowed_concepts"]
    assert "거듭제곱과 거듭제곱근" in profile["disallowed_concepts"]

    skill_index = profile["skill_index"]
    assert "원의 방정식의 표준형" in skill_index
    assert skill_index["원의 방정식의 표준형"]["id"] == 3142
    assert "두 점 사이의 거리" in skill_index
    assert skill_index["두 점 사이의 거리"]["id"] == 1442

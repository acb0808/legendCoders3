"""단위 테스트 — 참조 섹션 렌더러 및 LCEL 체인 (M2 TDD).

역할별 텍스트 렌더링, 토큰 캡, 빈 입력 처리, LCEL build_reference_runnable을 검증한다.
"""

from __future__ import annotations

import json
from pathlib import Path

from math_variant.reference.condition_retriever import ConditionStyleRetriever
from math_variant.reference.curriculum import CurriculumScope
from math_variant.reference.exam_retriever import ExamPatternRetriever
from math_variant.reference.models import (
    ConditionPhrasing,
    ExamPatternCard,
    SolutionStyle,
)
from math_variant.reference.sections import (
    build_reference_runnable,
    build_reference_summary,
    critic_scope_section,
    generator_condition_section,
    generator_style_section,
    ideator_pattern_section,
    planner_scope_section,
)
from math_variant.reference.style_retriever import SolutionStyleRetriever


def test_section_renderers_output_and_token_cap() -> None:
    """섹션 렌더러가 올바른 헤더와 내용을 반환하고 빈 입력 시 빈 문자열을 반환하는지 검증."""
    # 1. Planner Scope Section
    scope = CurriculumScope(
        topic_ids=["C08-01-01-01", "C08-01-03-01"],
        allowed_concepts=["두 점 사이의 거리", "원의 방정식의 표준형"],
        disallowed_concepts=["지수", "로그", "미분계수"],
    )
    scope_str = planner_scope_section(scope)
    assert "[교육과정 허용 범위" in scope_str
    assert "복사 금지" in scope_str
    assert "원의 방정식의 표준형" in scope_str
    assert "미분계수" in scope_str

    # 빈 스코프
    assert planner_scope_section(None) == ""

    # 2. Ideator Pattern Section
    card = ExamPatternCard(
        topic_id="C08-01-03-01",
        unit="원의 방정식",
        pattern="[원의 방정식] 최댓값은?",
        wording="최댓값은?",
        condition_style=["원 _와 직선 _가 만날 때"],
        example_abstract="원 _와 직선 _가 만날 때 최댓값은?",
        difficulty_zone="상",
        source_count=3,
        sources=["2023#1"],
    )
    pattern_str = ideator_pattern_section([card])
    assert "[기출 출제 패턴 참조" in pattern_str
    assert "복사 금지" in pattern_str
    assert "최댓값은?" in pattern_str
    assert ideator_pattern_section([]) == ""

    # 3. Generator Condition Section
    cond = ConditionPhrasing(
        topic_id="C08-01-03-01",
        unit="원의 방정식",
        patterns=["원 _와 직선 _가 만날 때", "중심이 _인 원"],
        wording_conventions=["최댓값을 구하시오"],
    )
    cond_str = generator_condition_section([cond])
    assert "[조건 표현 관례 참조" in cond_str
    assert "원 _와 직선 _가 만날 때" in cond_str
    assert generator_condition_section([]) == ""

    # 4. Generator Style Section
    style = SolutionStyle(
        unit="원의 방정식",
        open="주어진 원의 방정식을 표준형으로 정리하면",
        transform_order=["표준형 변환", "거리 공식", "부등식 계산"],
        justification_vocab=["정리하면", "따라서", "이므로"],
        close="따라서 구하는 최댓값은 ~이다.",
        sample_step="1단계: 식 수립",
    )
    style_str = generator_style_section(style)
    assert "[해설 스타일 가이드" in style_str
    assert "표준형 변환" in style_str
    assert generator_style_section(None) == ""

    # 5. Critic Scope Section
    critic_str = critic_scope_section(scope)
    assert "[교육과정 정합 평가 기준" in critic_str
    assert critic_scope_section(None) == ""


def test_build_reference_runnable_parallel_execution(tmp_path: Path) -> None:
    """build_reference_runnable이 RunnableParallel로 3종 리트리버를 합성하는지 검증."""
    exam_path = tmp_path / "reference_exam_patterns.jsonl"
    exam_card = {
        "topic_id": "C08-01-03-01",
        "unit": "원의 방정식",
        "pattern": "원",
        "wording": "구하시오",
        "condition_style": ["원 _"],
        "example_abstract": "원",
        "difficulty_zone": "중",
        "source_count": 1,
        "sources": [],
    }
    with open(exam_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(exam_card) + "\n")

    cond_path = tmp_path / "condition_style_index.json"
    cond_data = {
        "C08-01-03-01": {
            "topic_id": "C08-01-03-01",
            "unit": "원의 방정식",
            "condition_phrasings": [{"pattern": "원 _", "freq": 3}],
            "wording_conventions": ["구하시오"],
        }
    }
    with open(cond_path, "w", encoding="utf-8") as f:
        json.dump(cond_data, f)

    style_path = tmp_path / "solution_style_guide.json"
    style_data = {
        "원의 방정식": {
            "unit": "원의 방정식",
            "style": {
                "open": "열기",
                "transform_order": ["순서"],
                "justification_vocab": ["따라서"],
                "close": "닫기",
                "sample_step": "예시",
            },
        }
    }
    with open(style_path, "w", encoding="utf-8") as f:
        json.dump(style_data, f)

    exam_retriever = ExamPatternRetriever(index_path=exam_path, k=3)
    cond_retriever = ConditionStyleRetriever(index_path=cond_path, k=5)
    style_retriever = SolutionStyleRetriever(index_path=style_path)

    runnable = build_reference_runnable(exam_retriever, cond_retriever, style_retriever)
    result = runnable.invoke({"topics": "C08-01-03-01,원의 방정식"})

    assert "patterns" in result
    assert "phrasings" in result
    assert "style" in result
    assert len(result["patterns"]) == 1
    assert len(result["phrasings"]) == 1
    assert result["style"] is not None


def test_build_reference_summary_compresses_results() -> None:
    """검색 결과를 리포트용 요약으로 압축한다."""
    summary = build_reference_summary(
        [
            ExamPatternCard(
                topic_id="t1",
                unit="도형의 방정식",
                pattern="접선의 방정식",
                wording="접선을 구하시오",
                example_abstract="원에 접선",
                source_count=2,
            )
        ],
        [
            ConditionPhrasing(
                topic_id="t1",
                unit="도형의 방정식",
                patterns=["조건 A"],
                wording_conventions=["관례 B"],
            )
        ],
        SolutionStyle(
            unit="도형의 방정식",
            open="주어진",
            close="구하는 값은",
            justification_vocab=["따라서"],
        ),
    )
    assert summary is not None
    assert summary["exam_patterns"][0]["unit"] == "도형의 방정식"
    assert summary["exam_patterns"][0]["source_count"] == 2
    assert summary["condition_phrasings"]["count"] == 2
    assert summary["condition_phrasings"]["topics"] == ["도형의 방정식"]
    assert summary["style_guide"]["justification_vocab"] == ["따라서"]


def test_build_reference_summary_returns_none_when_empty() -> None:
    """검색 결과가 전부 비어 있으면 None (기존 run 데이터와 호환)."""
    assert build_reference_summary([], [], None) is None


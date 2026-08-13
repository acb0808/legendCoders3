"""역할별 참조 섹션 렌더러 및 LCEL 합성 체인 (M2).

에이전트별 프롬프트에 주입될 참조 섹션 문자열을 렌더링하고,
LangChain RunnableParallel 을 통해 3종 리트리버를 병렬 실행하는 체인을 구성한다.
"""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel

from math_variant.reference.condition_retriever import ConditionStyleRetriever
from math_variant.reference.exam_retriever import ExamPatternRetriever
from math_variant.reference.models import (
    ConditionPhrasing,
    CurriculumScope,
    ExamPatternCard,
    SolutionStyle,
)
from math_variant.reference.style_retriever import SolutionStyleRetriever


def planner_scope_section(scope: CurriculumScope | None) -> str:
    """PLANNER 역할에 주입될 교육과정 범위 참조 섹션을 렌더링한다 (~400 토큰)."""
    if not scope or (not scope.allowed_concepts and not scope.disallowed_concepts):
        return ""

    allowed_str = (
        ", ".join(scope.allowed_concepts[:15]) if scope.allowed_concepts else "(전체)"
    )
    disallowed_str = (
        ", ".join(scope.disallowed_concepts[:15]) if scope.disallowed_concepts else "(없음)"
    )

    return (
        "[교육과정 허용 범위 (참조용)]\n"
        "※ [복사 금지, 참조만] 아래 교육과정 허용/금지 범위를 준수하여 핵심 개념을 설정하십시오.\n"
        f"- 허용 개념: {allowed_str}\n"
        f"- 금지 개념(타 과목/단원): {disallowed_str}"
    )


def ideator_pattern_section(
    cards: list[ExamPatternCard] | list[Document] | list[dict[str, Any]], k: int = 3
) -> str:
    """IDEATOR 역할에 주입될 기출 출제 패턴 참조 섹션을 렌더링한다 (~250 토큰)."""
    if not cards:
        return ""

    lines: list[str] = [
        "[기출 출제 패턴 참조 (발문 및 구성 방식)]",
        "※ [복사 금지, 참조만] 아래 출제 양식을 참조하되, 원문 구성을 그대로 복제하지 마십시오.",
    ]

    selected = cards[:k]
    for idx, item in enumerate(selected, 1):
        if isinstance(item, ExamPatternCard):
            lines.append(f"{idx}. [{item.unit}] 발문 형태: {item.wording}")
            if item.condition_style:
                lines.append(f"   조건 관례: {', '.join(item.condition_style[:3])}")
        elif isinstance(item, Document):
            unit = item.metadata.get("unit", "수학")
            wording = item.metadata.get("wording", "표준 발문")
            lines.append(f"{idx}. [{unit}] 발문 형태: {wording}")
        elif isinstance(item, dict):
            unit = item.get("unit", "수학")
            wording = item.get("wording", "표준 발문")
            conds = item.get("condition_style", [])
            lines.append(f"{idx}. [{unit}] 발문 형태: {wording}")
            if conds:
                lines.append(f"   조건 관례: {', '.join(conds[:3])}")

    return "\n".join(lines)


def generator_condition_section(
    phrasings: list[ConditionPhrasing] | list[Document] | list[dict[str, Any]], k: int = 5
) -> str:
    """GENERATOR 역할에 주입될 조건 표현 관례 참조 섹션을 렌더링한다 (~350 토큰)."""
    if not phrasings:
        return ""

    lines: list[str] = [
        "[조건 표현 관례 참조]",
        "※ [복사 금지, 참조만] 학교 시험 표준 조건 표현 양식을 준수하여 문제를 서술하십시오.",
    ]

    selected = phrasings[:k]
    for idx, item in enumerate(selected, 1):
        if isinstance(item, ConditionPhrasing):
            pats = ", ".join(item.patterns[:3]) if item.patterns else "표준 표현"
            convs = (
                ", ".join(item.wording_conventions[:2])
                if item.wording_conventions
                else "표준 발문"
            )
            lines.append(f"{idx}. [{item.unit}] 빈출 표현: {pats} | 발문: {convs}")
        elif isinstance(item, Document):
            unit = item.metadata.get("unit", "수학")
            lines.append(f"{idx}. [{unit}] {item.page_content.splitlines()[0]}")
        elif isinstance(item, dict):
            unit = item.get("unit", "수학")
            pats = item.get("patterns", [])
            convs = item.get("wording_conventions", [])
            p_str = ", ".join(pats[:3]) if pats else "표준 표현"
            c_str = ", ".join(convs[:2]) if convs else "표준 발문"
            lines.append(f"{idx}. [{unit}] 빈출 표현: {p_str} | 발문: {c_str}")

    return "\n".join(lines)


def generator_style_section(
    style: SolutionStyle | Document | dict[str, Any] | None,
) -> str:
    """GENERATOR 역할에 주입될 해설 스타일 가이드 참조 섹션을 렌더링한다 (~250 토큰)."""
    if not style:
        return ""

    if isinstance(style, SolutionStyle):
        unit = style.unit
        open_p = style.open
        order_str = " -> ".join(style.transform_order) if style.transform_order else "식 전개"
        vocab_str = (
            ", ".join(style.justification_vocab)
            if style.justification_vocab
            else "정리하면, 따라서"
        )
        close_p = style.close
    elif isinstance(style, Document):
        meta_style = style.metadata.get("style", {})
        unit = style.metadata.get("unit", "수학")
        open_p = meta_style.get("open", "")
        order_str = " -> ".join(meta_style.get("transform_order", []))
        vocab_str = ", ".join(meta_style.get("justification_vocab", []))
        close_p = meta_style.get("close", "")
    elif isinstance(style, dict):
        style_obj = style.get("style", style)
        unit = style.get("unit", "수학")
        open_p = style_obj.get("open", "")
        order_str = " -> ".join(style_obj.get("transform_order", []))
        vocab_str = ", ".join(style_obj.get("justification_vocab", []))
        close_p = style_obj.get("close", "")
    else:
        return ""

    return (
        f"[해설 스타일 가이드 ({unit})]\n"
        "※ [복사 금지, 참조만] 아래 표준 서술 순서와 정당화 어휘를 준수하여 해설을 작성하십시오.\n"
        f"- 서술 도입: {open_p}\n"
        f"- 표준 전개 순서: {order_str}\n"
        f"- 권장 정당화 어휘: {vocab_str}\n"
        f"- 종결 양식: {close_p}"
    )


def critic_scope_section(scope: CurriculumScope | None) -> str:
    """CRITIC 역할에 주입될 교육과정 정합 평가 섹션을 렌더링한다 (~200 토큰)."""
    if not scope or not scope.disallowed_concepts:
        return ""

    disallowed_str = ", ".join(scope.disallowed_concepts[:12])
    return (
        "[교육과정 정합 평가 기준]\n"
        "※ 문제와 해설에 아래 금지 개념(타 과목/단원)이 포함되어 있으면 "
        "comments에 'CURRICULUM_VIOLATION'을 명시하고 recommendation을 'REVISE'로 판정하십시오.\n"
        f"- 허용 범위 외 금지 개념: {disallowed_str}"
    )


def build_reference_runnable(
    exam_retriever: ExamPatternRetriever,
    condition_retriever: ConditionStyleRetriever,
    style_retriever: SolutionStyleRetriever,
) -> Runnable[dict[str, str], dict[str, Any]]:
    """RunnableParallel 로 3종 리트리버를 병렬 실행하여 참조 데이터를 수집한다."""
    return RunnableParallel(
        patterns=RunnableLambda(lambda x: exam_retriever.get_cards(x["topics"])),
        phrasings=RunnableLambda(lambda x: condition_retriever.get_phrasings(x["topics"])),
        style=RunnableLambda(lambda x: style_retriever.get_style(x["topics"])),
    )

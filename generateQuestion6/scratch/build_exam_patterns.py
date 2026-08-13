"""기출 출제 패턴 카드 인덱스 생성 스크립트 (M1).

기출 구조화 시험지 JSON 파일들을 파싱하여 단원별 출제 패턴, 발문 관례,
조건 표현 n-gram을 추출하고 추상화된 패턴 카드(JSONL)를 생성한다.
원문 전체 문장은 저장하지 않는다.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 단원 판별 키워드 우선순위 매핑
_UNIT_KEYWORDS: list[tuple[str, str, list[str]]] = [
    ("원의 방정식", "C08-01-03-01", ["원", "접선", "반지름", "x^2 + y^2", "x^2+y^2", "중심"]),
    ("도형의 이동", "C08-01-04-01", ["평행이동", "대칭이동", "이동한 점", "이동한 원"]),
    ("직선의 방정식", "C08-01-02-01", ["직선", "수직", "기울기", "평행", "절편", "점과 직선"]),
    ("평면좌표", "C08-01-01-01", ["평면좌표", "내분", "외분", "무게중심", "두 점", "선분", "거리"]),
    ("집합", "C08-02-01-01", ["집합", "원소", "부분집합", "합집합", "교집합", "여집합", "차집합"]),
    ("명제", "C08-02-02-01", ["명제", "충분조건", "필요조건", "대우", "귀류법", "진리집합"]),
    ("유리함수", "C08-03-02-01", ["유리함수", "점근선", "분수함수"]),
    ("무리함수", "C08-03-03-01", ["무리함수", "근호", "\\sqrt"]),
    ("함수", "C08-03-01-01", ["일대일", "역함수", "합성함수", "치역", "공역", "정의역", "함수"]),
]

_WORDING_PATTERNS: list[tuple[str, str]] = [
    (r"최댓값과 최솟값의 (합|차)은\?", "최댓값과 최솟값의 합/차는?"),
    (r"최댓값은\?", "최댓값은?"),
    (r"최솟값은\?", "최솟값은?"),
    (r"상수 [a-zA-Z가-힣]+의 값은\?", "상수 값은?"),
    (r"모든 [a-zA-Z가-힣]+의 값의 합은\?", "모든 값의 합은?"),
    (r"값은\?", "값은?"),
    (r"개수는\?", "개수는?"),
    (r"옳은 것만을.*?고른 것은\?", "옳은 것은?"),
    (r"구하시오\.?", "구하시오"),
]


def _classify_unit(text: str) -> tuple[str, str]:
    """문항 텍스트에서 단원명과 대표 topic_id를 판별한다."""
    for unit_name, topic_id, keywords in _UNIT_KEYWORDS:
        if any(kw in text for kw in keywords):
            return unit_name, topic_id
    return "도형의 방정식", "C08-01-01-01"


def _extract_wording(text: str) -> str:
    """문항 텍스트 말미의 발문 관례를 추출한다."""
    for regex, desc in _WORDING_PATTERNS:
        if re.search(regex, text):
            return desc
    return "값을 구하는 일반 발문"


def _abstract_text(text: str) -> str:
    """수식 태그 및 구체적 변수/상수를 _ 자리표시자로 치환해 원문 복사를 방지한다."""
    abstracted = re.sub(r"<eq>.*?</eq>", "_", text)
    abstracted = re.sub(r"\$.*?\$", "_", abstracted)
    abstracted = re.sub(r"_+", "_", abstracted)
    abstracted = re.sub(r"\b\d+\b", "_", abstracted)
    return abstracted.strip()


def _extract_condition_phrases(abstracted_text: str) -> list[str]:
    """정규화된 텍스트에서 2~4어절의 조건 표현 패턴을 추출한다."""
    phrases: list[str] = []
    triggers = [
        "에 대하여", "일 때", "가 만날 때", "위의 점", "사이의 거리", "를 지나는", "와 접하는",
    ]
    sentences = re.split(r"[.\n]", abstracted_text)
    for sent in sentences:
        sent = sent.strip()
        for trigger in triggers:
            if trigger in sent:
                idx = sent.find(trigger)
                start = max(0, idx - 15)
                end = min(len(sent), idx + len(trigger) + 5)
                snippet = sent[start:end].strip()
                if snippet and snippet not in phrases:
                    phrases.append(snippet)
    return phrases[:5]


def extract_exam_patterns(
    exams_data: list[tuple[str, list[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    """시험지 문항 목록에서 단원별 추상화된 출제 패턴 카드를 생성한다."""
    grouped: dict[str, list[dict[str, Any]]] = {}

    for exam_name, questions in exams_data:
        for q in questions:
            q_text = str(q.get("question_text", ""))
            if not q_text.strip():
                continue
            unit_name, topic_id = _classify_unit(q_text)
            wording = _extract_wording(q_text)
            abstracted = _abstract_text(q_text)
            cond_phrases = _extract_condition_phrases(abstracted)
            q_num = str(q.get("question_number", "0"))
            score = str(q.get("score", "0.0"))

            entry = {
                "source": f"{exam_name}#{q_num}",
                "topic_id": topic_id,
                "unit": unit_name,
                "wording": wording,
                "condition_style": cond_phrases,
                "abstract": abstracted,
                "score": score,
            }
            grouped.setdefault(unit_name, []).append(entry)

    cards: list[dict[str, Any]] = []
    for unit_name, items in grouped.items():
        topic_id = items[0]["topic_id"]
        sources = [item["source"] for item in items]
        all_styles: list[str] = []
        for item in items:
            for st in item["condition_style"]:
                if st not in all_styles:
                    all_styles.append(st)

        scores = [
            float(item["score"])
            for item in items
            if item["score"].replace(".", "", 1).isdigit()
        ]
        avg_score = sum(scores) / len(scores) if scores else 4.0
        difficulty_zone = "상" if avg_score >= 4.3 else ("중" if avg_score >= 3.6 else "하")

        wording_summary = items[0]["wording"]
        abstract_sample = items[0]["abstract"]
        if len(abstract_sample) > 120:
            abstract_sample = abstract_sample[:120] + "..."

        cards.append(
            {
                "topic_id": topic_id,
                "unit": unit_name,
                "pattern": f"[{unit_name}] {wording_summary}",
                "wording": wording_summary,
                "condition_style": all_styles[:6],
                "example_abstract": abstract_sample,
                "difficulty_zone": difficulty_zone,
                "source_count": len(items),
                "sources": sources[:10],
            }
        )

    return cards


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / "reference_exam_patterns.jsonl"

    exam_dir_gq6 = project_root / "시험지"
    exam_dir_gq2 = project_root.parent / "generateQuestion2" / "시험지"
    target_exam_dir = exam_dir_gq6 if exam_dir_gq6.exists() else exam_dir_gq2

    exam_files = list(target_exam_dir.glob("*_structured.json"))
    exams_data: list[tuple[str, list[dict[str, Any]]]] = []
    for ef in exam_files:
        try:
            with open(ef, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    exams_data.append((ef.stem.replace("_structured", ""), data))
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", ef, exc)

    cards = extract_exam_patterns(exams_data)
    with open(out_path, "w", encoding="utf-8") as f:
        for card in cards:
            f.write(json.dumps(card, ensure_ascii=False) + "\n")

    print(f"Generated {len(cards)} exam pattern cards at {out_path}")


if __name__ == "__main__":
    main()

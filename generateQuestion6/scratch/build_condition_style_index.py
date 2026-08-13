"""조건 표현 관례 인덱스 생성 스크립트 (M1).

AI Hub 코퍼스(dataset_2nd_term_final)에서 C08(공통수학2) 문항을 필터링하고
단원별 빈출 조건절 패턴과 발문 관례를 집계하여 JSON 인덱스를 생성한다.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TRIGGERS = [
    "에 대하여",
    "일 때",
    "가 만날 때",
    "위의 점",
    "사이의 거리",
    "를 지나는",
    "와 접하는",
    "직교할 때",
    "평행할 때",
    "내분하는",
    "외분하는",
    "중점이",
    "꼭짓점으로",
]

_WORDING_SUFFIXES = [
    "구하시오",
    "값은?",
    "최댓값은?",
    "최솟값은?",
    "상수 a의 값은?",
    "개수는?",
    "옳은 것은?",
    "나타내시오",
]


def _normalize_clause(text: str) -> str:
    """수식($...$), LaTeX 태그, 숫자를 _ 로 치환한다."""
    t = re.sub(r"\$.*?\$", "_", text)
    t = re.sub(r"<eq>.*?</eq>", "_", t)
    t = re.sub(r"\b\d+\b", "_", t)
    t = re.sub(r"_+", "_", t)
    return t.strip()


def extract_condition_style_index(
    corpus_items: list[dict[str, Any]], min_freq: int = 2
) -> dict[str, Any]:
    """코퍼스 문항 목록에서 C08 토픽별 조건 표현 패턴과 발문 관례를 집계한다."""
    topic_phrasings: dict[str, Counter[str]] = {}
    topic_wordings: dict[str, Counter[str]] = {}
    topic_units: dict[str, str] = {}

    for item in corpus_items:
        q_info_list = item.get("question_info") or []
        if not q_info_list:
            continue
        q_info = q_info_list[0]
        topic_id = str(q_info.get("assigned_topic_id", ""))
        if not topic_id.startswith("C08"):
            continue

        raw_unit = (
            q_info.get("question_topic_name")
            or q_info.get("assigned_question_type")
            or "도형의 방정식"
        )
        topic_units[topic_id] = str(raw_unit)

        ocr_list = item.get("OCR_info") or []
        if not ocr_list:
            continue
        raw_text = str(ocr_list[0].get("question_text", ""))
        if not raw_text.strip():
            continue

        normalized = _normalize_clause(raw_text)

        sentences = re.split(r"[.\n]", normalized)
        for sent in sentences:
            sent = sent.strip()
            for trig in _TRIGGERS:
                if trig in sent:
                    idx = sent.find(trig)
                    start = max(0, idx - 12)
                    end = min(len(sent), idx + len(trig) + 3)
                    pattern = sent[start:end].strip()
                    if pattern:
                        topic_phrasings.setdefault(topic_id, Counter())[pattern] += 1

        for suffix in _WORDING_SUFFIXES:
            if suffix in raw_text:
                topic_wordings.setdefault(topic_id, Counter())[suffix] += 1
                break

    result: dict[str, Any] = {}
    for topic_id, unit_name in topic_units.items():
        phrasings_counter = topic_phrasings.get(topic_id, Counter())
        filtered_phrasings = [
            {"pattern": pat, "freq": count}
            for pat, count in phrasings_counter.most_common(10)
            if count >= min_freq
        ]

        wordings_counter = topic_wordings.get(topic_id, Counter())
        conventions = [w for w, _ in wordings_counter.most_common(5)]

        if not conventions:
            conventions = ["값을 구하시오", "상수의 값을 구하는 형태"]

        result[topic_id] = {
            "topic_id": topic_id,
            "unit": unit_name,
            "condition_phrasings": filtered_phrasings,
            "wording_conventions": conventions,
        }

    return result


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / "condition_style_index.json"

    corpus_root = project_root.parent / "generateQuestion2" / "dataset_2nd_term_final"
    corpus_files = list(corpus_root.glob("**/*.json"))

    corpus_items: list[dict[str, Any]] = []
    for cf in corpus_files:
        try:
            with open(cf, encoding="utf-8") as f:
                corpus_items.append(json.load(f))
        except Exception as exc:
            logger.debug("Skipping invalid corpus file %s: %s", cf, exc)

    index = extract_condition_style_index(corpus_items, min_freq=2)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"Generated condition style index for {len(index)} C08 topics at {out_path}")


if __name__ == "__main__":
    main()

"""개념서 해설 스타일 가이드 인덱스 생성 스크립트 (M1).

개념서 OCR 텍스트(json_data/개념서)를 파싱하여 단원별 표준 해설 서술 순서,
접속어, 정당화 어휘, 종결 어미를 규칙 기반으로 추출해 스타일 가이드 JSON을 생성한다.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CONNECTORS = [
    "정리하면",
    "따라서",
    "즉",
    "주어진",
    "그러므로",
    "이므로",
    "대입하면",
    "연립하면",
    "양변을",
    "인수분해하면",
]

_UNIT_TRANSFORM_ORDERS: dict[str, list[str]] = {
    "원의 방정식": [
        "표준형으로 정리하여 중심과 반지름 도출",
        "원과 직선 사이의 거리(d) 또는 판별식(D) 적용",
        "부등식/방정식 계산 및 상수 도출",
    ],
    "평면좌표": [
        "선분의 길이 공식 또는 내분/외분 공식 적용",
        "좌표 간의 관계식 수립",
        "거리/좌표 계산 및 최솟값 도출",
    ],
    "직선의 방정식": [
        "기울기와 지나는 한 점으로 직선의 방정식 작성",
        "수직/평행 조건 또는 교점 연립",
        "미정계수 및 절편 계산",
    ],
    "도형의 이동": [
        "평행이동/대칭이동 변환 규칙 적용",
        "이동된 도형의 방정식 수립",
        "기하학적 조건 확인",
    ],
    "집합": [
        "조건제시법을 원소나열법으로 표현",
        "벤다이어그램 또는 포함 관계 수립",
        "원소의 개수 공식 적용",
    ],
    "명제": [
        "가정과 결론의 진리집합 확인",
        "대우 명제 수립 또는 귀류법 전개",
        "충분조건/필요조건 판별",
    ],
    "함수": [
        "정의역과 공역의 대응 관계 확인",
        "일대일 대응 또는 합성함수/역함수 식 전개",
        "함숫값 계산",
    ],
}


def _classify_concept_unit(item: dict[str, Any]) -> str:
    """개념서 항목에서 단원명을 판별한다."""
    if item.get("unit"):
        return str(item["unit"])
    path_str = str(
        item.get("target_json_path")
        or item.get("source_image_path")
        or item.get("filename")
        or ""
    )
    units = [
        "원의 방정식",
        "도형의 이동",
        "직선의 방정식",
        "평면좌표",
        "집합",
        "명제",
        "함수",
        "유리함수",
        "무리함수",
    ]
    for u in units:
        if u in path_str:
            return u
    text = str(item.get("converted_text") or item.get("extracted_text") or "")
    for u in units:
        if u in text:
            return u
    return "도형의 방정식"


def extract_solution_style_guide(concept_items: list[dict[str, Any]]) -> dict[str, Any]:
    """개념서 문항 목록에서 단원별 해설 스타일 가이드를 추출한다."""
    grouped_texts: dict[str, list[str]] = {}

    for item in concept_items:
        unit = _classify_concept_unit(item)
        text = str(item.get("converted_text") or item.get("extracted_text") or "")
        if text.strip():
            grouped_texts.setdefault(unit, []).append(text)

    guide: dict[str, Any] = {}
    for unit, texts in grouped_texts.items():
        vocab_counter: Counter[str] = Counter()
        for t in texts:
            for conn in _CONNECTORS:
                if conn in t:
                    vocab_counter[conn] += 1

        common_vocab = [v for v, _ in vocab_counter.most_common(6)]
        if not common_vocab:
            common_vocab = ["정리하면", "따라서", "이므로", "대입하면"]

        transform_order = _UNIT_TRANSFORM_ORDERS.get(
            unit, ["주어진 조건을 수학적 식으로 정형화", "공식 및 정리 적용", "최종 정답 도출"]
        )

        open_phrase = f"주어진 {unit}의 조건을 정리하면"
        close_phrase = "따라서 구하는 값은 ~이다."

        sample_step = (
            f"1단계: {open_phrase} 식을 세운다. "
            f"2단계: {transform_order[0]}을(를) 적용한다. "
            f"3단계: {close_phrase}"
        )

        guide[unit] = {
            "unit": unit,
            "style": {
                "open": open_phrase,
                "transform_order": transform_order,
                "justification_vocab": common_vocab,
                "close": close_phrase,
                "sample_step": sample_step,
            },
        }

    for default_unit, transform_order in _UNIT_TRANSFORM_ORDERS.items():
        if default_unit not in guide:
            guide[default_unit] = {
                "unit": default_unit,
                "style": {
                    "open": f"주어진 {default_unit}의 조건을 정리하면",
                    "transform_order": transform_order,
                    "justification_vocab": ["정리하면", "따라서", "이므로", "대입하면"],
                    "close": "따라서 구하는 값은 ~이다.",
                    "sample_step": f"1단계: 식 수립. 2단계: {transform_order[0]}. 3단계: 정답 도출",
                },
            }

    return guide


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / "solution_style_guide.json"

    concept_root = project_root.parent / "generateQuestion2" / "json_data" / "개념서"
    concept_files = list(concept_root.glob("**/*.json"))

    concept_items: list[dict[str, Any]] = []
    for cf in concept_files:
        try:
            with open(cf, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    concept_items.append(data)
        except Exception as exc:
            logger.debug("Skipping invalid concept file %s: %s", cf, exc)

    guide = extract_solution_style_guide(concept_items)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(guide, f, ensure_ascii=False, indent=2)

    print(f"Generated solution style guide for {len(guide)} units at {out_path}")


if __name__ == "__main__":
    main()

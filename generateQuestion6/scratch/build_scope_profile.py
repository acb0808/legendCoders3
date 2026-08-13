"""교육과정 범위 프로파일 및 지식체계 인덱스 생성 스크립트 (M1).

math_curriculum_db.csv 와 수학_지식체계_데이터_세트를 파싱하여
C08(공통수학2) 허용 토픽, C09 이상 금지 개념, 개념명-스킬ID 매핑 인덱스를 생성한다.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _read_csv_text(csv_path: Path) -> str:
    """인코딩(utf-8-sig, utf-8, cp949, euc-kr)을 순차 시도하여 CSV 텍스트를 읽는다."""
    raw = csv_path.read_bytes()
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def extract_scope_profile(
    csv_content: str, knowledge_data: dict[str, Any]
) -> dict[str, Any]:
    """CSV 내용과 지식체계 JSON 데이터에서 교육과정 범위 프로파일을 생성한다."""
    reader = csv.reader(io.StringIO(csv_content.strip()))
    _ = next(reader, None)

    topic_ids: list[str] = []
    allowed_concepts_set: set[str] = set()
    disallowed_concepts_set: set[str] = set()
    skill_descriptions: dict[str, str] = {}

    for row in reader:
        if not row or not row[0].strip():
            continue
        topic_id = row[0].strip()
        topic_name = row[4].strip() if len(row) > 4 and row[4].strip() else ""

        if topic_id.startswith("C08"):
            topic_ids.append(topic_id)
            if topic_name:
                allowed_concepts_set.add(topic_name)
                skill_descriptions[topic_id] = topic_name
        elif topic_id.startswith(("C09", "C1", "C2")):
            if topic_name:
                disallowed_concepts_set.add(topic_name)

    skill_index: dict[str, dict[str, Any]] = {}
    for item in knowledge_data.values():
        if not isinstance(item, dict):
            continue
        for key in ["fromConcept", "toConcept"]:
            concept = item.get(key)
            if isinstance(concept, dict) and "name" in concept:
                c_name = str(concept["name"]).strip()
                c_id = concept.get("id")
                c_semester = str(concept.get("semester", ""))
                c_desc = str(concept.get("description", ""))
                if c_name and c_name not in skill_index:
                    skill_index[c_name] = {
                        "id": c_id,
                        "semester": c_semester,
                        "description": c_desc,
                    }

    return {
        "topic_ids": topic_ids,
        "allowed_concepts": sorted(allowed_concepts_set),
        "disallowed_concepts": sorted(disallowed_concepts_set),
        "skill_descriptions": skill_descriptions,
        "skill_index": skill_index,
    }


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / "scope_profile.json"

    csv_path = project_root.parent / "generateQuestion2" / "math_curriculum_db.csv"
    knowledge_path = (
        project_root.parent / "generateQuestion2" / "수학_지식체계_데이터_세트_210611.json"
    )

    csv_text = _read_csv_text(csv_path) if csv_path.exists() else ""
    knowledge_data: dict[str, Any] = {}
    if knowledge_path.exists():
        try:
            with open(knowledge_path, encoding="utf-8") as f:
                knowledge_data = json.load(f)
        except Exception as exc:
            logger.warning("Failed to load knowledge JSON: %s", exc)

    profile = extract_scope_profile(csv_text, knowledge_data)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    print(
        f"Generated scope profile ({len(profile['topic_ids'])} C08 topics, "
        f"{len(profile['allowed_concepts'])} allowed concepts, "
        f"{len(profile['skill_index'])} skills) at {out_path}"
    )


if __name__ == "__main__":
    main()

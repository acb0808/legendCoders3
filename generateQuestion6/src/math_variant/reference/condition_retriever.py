"""조건 표현 관례 리트리버 (M2).

LangChain BaseRetriever 를 상속하여 조건 표현 관례 인덱스를 검색한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

from math_variant.reference.models import ConditionPhrasing


class ConditionStyleRetriever(BaseRetriever):
    """조건 표현 관례 검색기."""

    index_path: Path
    k: int = 5
    index_data: dict[str, ConditionPhrasing] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        if not self.index_data and self.index_path.exists():
            loaded: dict[str, ConditionPhrasing] = {}
            with open(self.index_path, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for tid, val in data.items():
                        if isinstance(val, dict):
                            patterns = [
                                p.get("pattern", "") if isinstance(p, dict) else str(p)
                                for p in val.get("condition_phrasings", [])
                            ]
                            loaded[tid] = ConditionPhrasing(
                                topic_id=tid,
                                unit=str(val.get("unit", "")),
                                patterns=[p for p in patterns if p],
                                wording_conventions=list(val.get("wording_conventions", [])),
                            )
            object.__setattr__(self, "index_data", loaded)

    def get_phrasings(self, query: str) -> list[ConditionPhrasing]:
        """주어진 토픽 질의에 정합하는 조건 표현 관례 목록을 반환한다."""
        tokens = [t.strip() for t in query.split(",") if t.strip()]
        if not tokens or not self.index_data:
            return []

        matched: list[ConditionPhrasing] = []

        # 1. topic_id 완전 일치
        for token in tokens:
            if token in self.index_data and self.index_data[token] not in matched:
                matched.append(self.index_data[token])

        # 2. unit 부분 일치
        if not matched:
            for token in tokens:
                for phr in self.index_data.values():
                    if (token in phr.unit or phr.unit in token) and phr not in matched:
                        matched.append(phr)

        # 3. 상위 단원 폴백
        if not matched:
            for token in tokens:
                if "-" in token:
                    prefix = "-".join(token.split("-")[:2])
                    for phr in self.index_data.values():
                        if phr.topic_id.startswith(prefix) and phr not in matched:
                            matched.append(phr)

        return matched[: self.k]

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun | None = None
    ) -> list[Document]:
        phrasings = self.get_phrasings(query)
        docs: list[Document] = []
        for phr in phrasings:
            patterns_str = "\n- ".join(phr.patterns) if phr.patterns else "(없음)"
            conventions_str = (
                ", ".join(phr.wording_conventions) if phr.wording_conventions else "(없음)"
            )
            content = (
                f"단원: {phr.unit}\n"
                f"빈출 조건절 패턴:\n- {patterns_str}\n"
                f"발문 관례: {conventions_str}"
            )
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "topic_id": phr.topic_id,
                        "unit": phr.unit,
                        "phrasing": phr.model_dump(),
                    },
                )
            )
        return docs

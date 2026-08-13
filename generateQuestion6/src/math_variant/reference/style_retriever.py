"""해설 스타일 가이드 리트리버 (M2).

LangChain BaseRetriever 를 상속하여 단원별 해설 스타일 가이드를 검색한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

from math_variant.reference.models import SolutionStyle


class SolutionStyleRetriever(BaseRetriever):
    """해설 서술 스타일 검색기."""

    index_path: Path
    styles: dict[str, SolutionStyle] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        if not self.styles and self.index_path.exists():
            loaded: dict[str, SolutionStyle] = {}
            with open(self.index_path, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for unit_name, val in data.items():
                        if isinstance(val, dict):
                            style_info = val.get("style", {}) if "style" in val else val
                            loaded[unit_name] = SolutionStyle(
                                unit=unit_name,
                                open=str(style_info.get("open", "")),
                                transform_order=list(style_info.get("transform_order", [])),
                                justification_vocab=list(style_info.get("justification_vocab", [])),
                                close=str(style_info.get("close", "")),
                                sample_step=str(style_info.get("sample_step", "")),
                            )
            object.__setattr__(self, "styles", loaded)

    def get_style(self, query: str) -> SolutionStyle | None:
        """주어진 단원 질의에 정합하는 해설 스타일 가이드를 반환한다."""
        tokens = [t.strip() for t in query.split(",") if t.strip()]
        if not tokens or not self.styles:
            return None

        # 1. 완전 일치
        for token in tokens:
            if token in self.styles:
                return self.styles[token]

        # 2. 부분 일치
        for token in tokens:
            for unit_name, style in self.styles.items():
                if token in unit_name or unit_name in token:
                    return style

        return None

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun | None = None
    ) -> list[Document]:
        style = self.get_style(query)
        if not style:
            return []

        transform_str = " -> ".join(style.transform_order) if style.transform_order else "(표준)"
        vocab_str = ", ".join(style.justification_vocab) if style.justification_vocab else "(표준)"
        content = (
            f"단원: {style.unit}\n"
            f"서술 시작: {style.open}\n"
            f"식 변환 순서: {transform_str}\n"
            f"정당화 어휘: {vocab_str}\n"
            f"종결 어미: {style.close}\n"
            f"예시 단계: {style.sample_step}"
        )
        return [
            Document(
                page_content=content,
                metadata={"unit": style.unit, "style": style.model_dump()},
            )
        ]

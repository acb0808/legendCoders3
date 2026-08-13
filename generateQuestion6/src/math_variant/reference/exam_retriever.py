"""기출 출제 패턴 리트리버 (M2).

LangChain BaseRetriever 를 상속하여 기출 출제 패턴 카드를 검색한다.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

from math_variant.reference.models import ExamPatternCard

logger = logging.getLogger(__name__)


class ExamPatternRetriever(BaseRetriever):
    """기출 출제 패턴 검색기."""

    index_path: Path
    k: int = 3
    cards: list[ExamPatternCard] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        if not self.cards and self.index_path.exists():
            loaded_cards: list[ExamPatternCard] = []
            with open(self.index_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            loaded_cards.append(ExamPatternCard.model_validate_json(line))
                        except Exception as exc:
                            logger.debug("Skipping invalid line: %s", exc)
            object.__setattr__(self, "cards", loaded_cards)

    def get_cards(self, query: str) -> list[ExamPatternCard]:
        """주어진 토픽 질의에 정합하는 패턴 카드 목록을 반환한다."""
        tokens = [t.strip() for t in query.split(",") if t.strip()]
        if not tokens or not self.cards:
            return []

        matched: list[ExamPatternCard] = []

        # 1. topic_id 완전 일치
        for token in tokens:
            for card in self.cards:
                if card.topic_id == token and card not in matched:
                    matched.append(card)

        # 2. unit 부분 일치
        if not matched:
            for token in tokens:
                for card in self.cards:
                    if (token in card.unit or card.unit in token) and card not in matched:
                        matched.append(card)

        # 3. 상위 단원(접두사, e.g. C08-01) 폴백
        if not matched:
            for token in tokens:
                if "-" in token:
                    prefix = "-".join(token.split("-")[:2])
                    for card in self.cards:
                        if card.topic_id.startswith(prefix) and card not in matched:
                            matched.append(card)

        return matched[: self.k]

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun | None = None
    ) -> list[Document]:
        cards = self.get_cards(query)
        docs: list[Document] = []
        for card in cards:
            content = (
                f"출제 패턴: {card.pattern}\n"
                f"대표 발문: {card.wording}\n"
                f"조건 표현: {', '.join(card.condition_style)}\n"
                f"예시: {card.example_abstract}"
            )
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "topic_id": card.topic_id,
                        "unit": card.unit,
                        "wording": card.wording,
                        "card": card.model_dump(),
                    },
                )
            )
        return docs

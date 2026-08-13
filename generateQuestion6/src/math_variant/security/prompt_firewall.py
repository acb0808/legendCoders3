"""프롬프트 방화벽 — 블라인드 풀이 요청에서 금지 정보를 차단한다 (T05.3).

풀이기 입력에서 원문 정답·해설·변형 계획·생성기 주장 답을 제거하고,
금지 필드가 남아 있으면 정책 위반으로 기록한다.
"""

from __future__ import annotations

import re


class ForbiddenContentScanner:
    """금지 필드(라벨·값)가 프롬프트에 있는지 검사한다."""

    def __init__(self, forbidden: dict[str, str]) -> None:
        self._labels = [re.escape(label) for label in forbidden]
        self._values = [re.escape(value) for value in forbidden.values() if value]
        self._has_pattern = bool(self._labels or self._values)
        # 빈 정규식(re.compile('')) 은 모든 텍스트에 매칭되므로,
        # 금지 항목이 없으면 패턴 자체를 만들지 않는다. (웹 파이프라인은 빈 dict 를 넘긴다)
        self._pattern = (
            re.compile("|".join([*self._labels, *self._values]), re.IGNORECASE)
            if self._has_pattern
            else None
        )

    def scan(self, text: str) -> bool:
        """금지 콘텐츠가 하나라도 있으면 True."""
        if self._pattern is None:
            return False
        return self._pattern.search(text) is not None

    def matches(self, text: str) -> list[str]:
        if self._pattern is None:
            return []
        return list(dict.fromkeys(self._pattern.findall(text)))


def sanitize_blind_prompt(source_text: str) -> str:
    """원문에서 제공 답/해설 꼬리를 제거한다.

    시험지 텍스트에는 문제 뒤에 제공 답이 이어 붙는 경우가 많다.
    '답:'·'정답' 이후 부분과 문제의 마지막 답안 표기를 잘라낸다.
    """
    text = source_text
    for marker in ["답:", "답 :", "정답:", "정답 :", "답)", "정답)"]:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
    # 'y = ...' 또는 'x = ...' 로 끝나는 답안 표기 제거
    answer_tail = re.compile(r"\s*[A-Za-z]\s*=\s*[^\s]+(\s*또는\s*[A-Za-z]\s*=\s*[^\s]+)*\s*$")
    text = answer_tail.sub("", text)
    return text.strip()

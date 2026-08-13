"""원문 vs 후보의 결정적(비LLM) 표현 유사성 검사.

표현 복제(원문 문장을 그대로 쓰는 문제)를 차단하기 위한 보조 필터다.
아이디어 수준의 참신성은 Critic 이 담당하고, 여기서는 문자열 유사성을 결정적으로
판정해 "어느 구간이 일치하는지" 까지 보고한다 (피드백 루프 입력).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_STRIP = re.compile(r"[\s\u3000，。！？·、·\.\.,:;:()\[\]{}<>\"'‘’“”=+\-*/^_\\|~`!@#$%&]")

_LCS_THRESHOLD = 20      # 최장 공통 부분문자열 최대 길이 기준
_NGRAM_THRESHOLD = 0.55  # 문자 3-gram 유사도 기준


def normalize_text(text: str) -> str:
    """공백·구두점·수식 기호를 제거해 비교 가능한 형태로 만든다."""
    return _STRIP.sub("", text)


def longest_common_substring(a: str, b: str) -> tuple[int, int, int]:
    """최장 공통 부분문자열 (길이, a 시작 인덱스, b 시작 인덱스)."""
    if not a or not b:
        return 0, 0, 0
    prev = [0] * (len(b) + 1)
    best = 0
    best_a = 0
    best_b = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
                    best_a = i - best
                    best_b = j - best
        prev = cur
    return best, best_a, best_b


def ngram_similarity(a: str, b: str, n: int = 3) -> float:
    """문자 n-gram 의 Jaccard 유사도."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    grams_a = {a[i : i + n] for i in range(len(a) - n + 1)}
    grams_b = {b[i : i + n] for i in range(len(b) - n + 1)}
    if not grams_a or not grams_b:
        return 0.0
    return len(grams_a & grams_b) / len(grams_a | grams_b)


@dataclass(frozen=True)
class SimilarityReport:
    too_similar: bool
    lcs_len: int
    ngram_score: float
    match_snippet: str = ""


def similarity_report(source_text: str, candidate_text: str) -> SimilarityReport:
    """원문과 후보의 표현 유사성을 판정한다. 일치 구간 스니펫을 포함한다."""
    src = normalize_text(source_text)
    cand = normalize_text(candidate_text)
    if not src or not cand:
        return SimilarityReport(False, 0, 0.0)
    lcs_len, a_start, _b_start = longest_common_substring(src, cand)
    ngram = ngram_similarity(src, cand)
    too_similar = lcs_len > _LCS_THRESHOLD or ngram > _NGRAM_THRESHOLD
    snippet = src[a_start : a_start + lcs_len] if too_similar else ""
    return SimilarityReport(too_similar, lcs_len, ngram, snippet)

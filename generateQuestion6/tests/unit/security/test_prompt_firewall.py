"""프롬프트 방화벽 — 빈 금지 설정에서 오탐하지 않는지 테스트 (회귀)."""

from __future__ import annotations

from math_variant.security.prompt_firewall import (
    ForbiddenContentScanner,
    sanitize_blind_prompt,
)


def test_empty_forbidden_never_flags() -> None:
    """금지 정보가 없으면 어떤 입력도 위반으로 판정하지 않는다.

    re.compile('') (빈 정규식) 은 모든 텍스트에 매칭되어 scan 이 항상 True 가 된다.
    웹 파이프라인은 forbidden_context 를 전달하지 않으므로 반드시 False 여야 한다. (회귀)
    """
    scanner = ForbiddenContentScanner({})
    assert scanner.scan("직선 위의 점 P에서 축에 내린 수선의 발을 H라 하자") is False
    assert scanner.matches("삼각형 OPH의 넓이가 9이다") == []


def test_forbidden_value_detected() -> None:
    scanner = ForbiddenContentScanner({"원문 정답": "x = 3", "해설": ""})
    assert scanner.scan("문제가 있다. 정답은 x = 3 이다") is True
    assert scanner.matches("x = 3") == ["x = 3"]


def test_sanitize_blind_prompt_removes_answer_tail() -> None:
    text = "점 P의 좌표를 구하시오. x = 1 또는 x = -1"
    assert sanitize_blind_prompt(text) == "점 P의 좌표를 구하시오."

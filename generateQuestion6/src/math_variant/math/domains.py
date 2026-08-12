"""정의역 추출·가정 연결 (T02.2).

분모 0, 짝수 근호(radicand ≥ 0), 실수 기호 가정 등 숨은 예외를 표현식에서 찾아
기호별 가정으로 연결한다. 정의역 위반을 자동 통과시키지 않기 위한 결정론적 도구다.
"""

from __future__ import annotations

import sympy

from math_variant.math.expressions import SympyExpr

_DOMAIN_SYMBOLS: dict[str, sympy.Basic] = {
    "x": sympy.Symbol("x", real=True),
    "y": sympy.Symbol("y", real=True),
    "a": sympy.Symbol("a", real=True),
    "b": sympy.Symbol("b", real=True),
    "k": sympy.Symbol("k", real=True),
    "m": sympy.Symbol("m", real=True),
    "n": sympy.Symbol("n", integer=True, positive=True),
    "t": sympy.Symbol("t", real=True),
    "theta": sympy.Symbol("theta", real=True),
    "N": sympy.Symbol("N", integer=True, nonnegative=True),
    "r": sympy.Symbol("r", real=True, nonnegative=True),
}


def real_domain_assumptions(symbols: set[str]) -> dict[str, str]:
    """선언된 기호에 실수 가정을 연결해 정의역 정보를 반환한다."""
    return {
        sym: str(_DOMAIN_SYMBOLS[sym].assumptions0) for sym in symbols if sym in _DOMAIN_SYMBOLS
    }


def collect_implicit_restrictions(expr: SympyExpr) -> list[str]:
    """표현식에 숨어 있는 정의역 제약을 문자열로 추출한다.

    - 분모: denominator != 0
    - 짝수 근호: radicand >= 0
    - 로그/유리식 등 추가 제약은 후속 verifier 가 처리한다.
    """
    restrictions: list[str] = []

    for sub in sympy.preorder_traversal(expr):
        if isinstance(sub, sympy.Pow) and sub.exp.is_negative:
            restrictions.append(f"{sympy.sstr(sub.base)} != 0")

    for sub in sympy.preorder_traversal(expr):
        if (
            isinstance(sub, sympy.Pow)
            and sub.exp.is_Rational
            and sub.exp.p == 1
            and sub.exp.q % 2 == 0
        ):
            restrictions.append(f"{sympy.sstr(sub.base)} >= 0")

    return sorted(set(restrictions))


def substitute_in_domain(expr: SympyExpr, symbol_map: dict[str, sympy.Basic]) -> SympyExpr:
    """표현식의 기호를 도메인 가정이 있는 기호로 치환한다."""
    subs = {sympy.Symbol(name): sym for name, sym in symbol_map.items()}
    return expr.subs(subs)

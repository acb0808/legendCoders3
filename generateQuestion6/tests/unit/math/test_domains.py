"""T02.2 — 정의역 처리 보조 테스트."""

from __future__ import annotations

from math_variant.math.domains import (
    collect_implicit_restrictions,
    real_domain_assumptions,
)
from math_variant.math.expressions import parse_expression

_SYMS = {"x", "y", "a", "b", "k", "m", "n", "t", "theta"}


def test_denominator_restriction_detected() -> None:
    expr = parse_expression("1/(x-1)", symbols=_SYMS)
    restrictions = collect_implicit_restrictions(expr.raw)

    assert any("x - 1" in r and "!=" in r for r in restrictions), restrictions


def test_even_radicand_restriction_detected() -> None:
    expr = parse_expression("sqrt(4-x)", symbols=_SYMS)
    restrictions = collect_implicit_restrictions(expr.raw)

    assert any(r.endswith(">= 0") for r in restrictions), restrictions


def test_real_assumptions_connected_to_symbols() -> None:
    assumptions = real_domain_assumptions({"x", "n"})
    assert "real" in assumptions["x"]
    assert "integer" in assumptions["n"]

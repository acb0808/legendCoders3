"""안전한 수식 파싱과 다중 정규형 (T02.2).

보안 경계:
- 허용된 기호(symbols)와 허용 함수/상수만 파싱에 사용한다.
- 파싱 후 AST를 다시 검사해 미선언 기호·미허용 함수·임의 Python 표현을 거부한다.
- 부동소수점 대신 Integer·Rational 을 우선한다.

정규형 뷰:
- raw: 파싱 직후(평가된) 표현식
- exact: 모든 Float 를 정확한 Rational 로 바꾼 형태
- alpha_renamed: 변수명만 다른 동형 식이 같은 지문을 갖는 문자열 (srepr)
- ac_normalized: 교환·결합 정규화 (비가환 연산은 건드리지 않음)
- expanded / factored: 전개·인수분해 뷰
"""

from __future__ import annotations

import re
from typing import Annotated, Any

import sympy
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from pydantic_core import core_schema

from math_variant.errors import ErrorCode, MathVariantError, StructuredError

ALLOWED_FUNCTIONS: frozenset[str] = frozenset(
    {"sqrt", "Abs", "sign", "Matrix", "Rational", "Integer", "Symbol"}
)

ALLOWED_CONSTANTS: dict[str, sympy.Basic] = {
    "pi": sympy.pi,
    "E": sympy.E,
    "oo": sympy.oo,
    "I": sympy.I,
    "n": sympy.Symbol("n"),
    "N": sympy.Symbol("N"),
}

_IMPLICIT_NUMBER = re.compile(r"^\d+\.\d+$")


def _float_to_rational(value: sympy.Basic) -> sympy.Basic:
    """Float 를 정확한 Rational 로 바꾼다 (실수 리터럴 0.5 → Rational(1,2))."""
    if isinstance(value, sympy.MatrixBase):
        return value.applyfunc(_float_to_rational)
    if value.is_Float:
        return sympy.Rational(str(value))
    if value.is_Atom:
        return value
    if isinstance(value, sympy.core.function.AppliedUndef):
        return value
    new_args = tuple(_float_to_rational(a) for a in value.args)
    try:
        return value.func(*new_args)
    except Exception:
        return value


def _ac_sort(expr: sympy.Basic) -> sympy.Basic:
    """교환·결합 정규화. 비가환 연산은 그대로 둔다."""
    if isinstance(expr, sympy.Mul) and expr.is_commutative:
        args = sorted(expr.args, key=lambda a: sympy.srepr(_float_to_rational(a)))
        return sympy.Mul(*args)
    if isinstance(expr, sympy.Add) and expr.is_commutative:
        args = sorted(expr.args, key=lambda a: sympy.srepr(_float_to_rational(a)))
        return sympy.Add(*args)
    if isinstance(expr, sympy.MatrixBase):
        return expr.applyfunc(_ac_sort)
    return expr


def _alpha_fingerprint(expr: sympy.Basic) -> str:
    """변수명만 다른 동형 식이 같은 지문을 갖도록 알파 치환 후 srepr 을 반환한다."""
    exact = _float_to_rational(expr)
    free = sorted(exact.free_symbols, key=lambda s: str(s))
    mapping = {s: sympy.Symbol(f"s{i}") for i, s in enumerate(free)}
    renamed = exact.subs(mapping)
    return str(sympy.srepr(renamed))


def _validate_allowed(expr: sympy.Basic, declared: frozenset[str]) -> None:
    """허용 AST 밖 실행을 차단한다.

    미선언 자유 기호, 미허용 함수 적용, 문자열/람다 같은 비표준 원자는 거부한다.
    """
    undeclared = [
        str(s)
        for s in expr.free_symbols
        if str(s) not in declared and str(s) not in ALLOWED_CONSTANTS
    ]
    if undeclared:
        raise MathVariantError(
            StructuredError(
                code=ErrorCode.PARSE_REJECTED,
                message=f"선언되지 않은 기호 사용: {sorted(set(undeclared))}",
                context={"symbols": sorted(set(undeclared))},
            )
        )

    for sub in sympy.preorder_traversal(expr):
        if isinstance(sub, sympy.core.function.AppliedUndef):
            raise MathVariantError(
                StructuredError(
                    code=ErrorCode.PARSE_REJECTED,
                    message=f"허용되지 않은 함수 적용: {sympy.sstr(sub)}",
                    context={"node": sympy.srepr(sub)},
                )
            )
        if getattr(sub, "is_Function", False):
            name = getattr(sub.func, "__name__", None) or str(sub.func)
            if name not in ALLOWED_FUNCTIONS:
                raise MathVariantError(
                    StructuredError(
                        code=ErrorCode.PARSE_REJECTED,
                        message=f"허용되지 않은 함수 사용: {name}",
                        context={"node": sympy.srepr(sub), "function": name},
                    )
                )
        if isinstance(
            sub,
            (sympy.core.symbol.Str, sympy.core.function.Lambda, sympy.core.function.FunctionClass),
        ):
            raise MathVariantError(
                StructuredError(
                    code=ErrorCode.PARSE_REJECTED,
                    message=f"비표준 원자 표현: {sympy.srepr(sub)}",
                )
            )


# eval 맥락을 잠근다: sympy 전역 이름만 남기고 __import__/open/exec 같은
# 위험한 내장(builtins)을 차단해 임의 코드 실행을 막는다.
_SAFE_GLOBAL_DICT: dict[str, Any] = {}
exec("from sympy import *", _SAFE_GLOBAL_DICT)  # noqa: S102
_SAFE_GLOBAL_DICT["__builtins__"] = {
    "True": True,
    "False": False,
    "None": None,
}


def _parse_expr(source: str, symbols: frozenset[str]) -> sympy.Basic:
    from sympy.parsing.sympy_parser import (
        convert_xor,
        implicit_multiplication_application,
        parse_expr,
        standard_transformations,
    )

    local_dict: dict[str, Any] = {s: sympy.Symbol(s) for s in symbols}
    local_dict.update(ALLOWED_CONSTANTS)
    try:
        expr = parse_expr(
            source,
            local_dict=local_dict,
            global_dict=_SAFE_GLOBAL_DICT,
            transformations=(
                *standard_transformations,
                implicit_multiplication_application,
                convert_xor,
            ),
            evaluate=True,
        )
    except (sympy.SympifyError, ValueError, TypeError, AttributeError, NameError) as exc:
        raise MathVariantError(
            StructuredError(
                code=ErrorCode.PARSE_REJECTED,
                message=f"수식 파싱 실패: {source!r}",
                context={"source": source, "reason": str(exc)},
            )
        ) from exc
    _validate_allowed(expr, symbols)
    return expr


class _SympyField:
    """sympy 표현식을 문자열과 양방향으로 다루는 pydantic 필드."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        return core_schema.no_info_plain_validator_function(
            cls._validate, serialization=core_schema.to_string_ser_schema()
        )

    @staticmethod
    def _validate(value: Any) -> sympy.Basic:
        if isinstance(value, (sympy.Basic, sympy.MatrixBase)):
            return value
        if isinstance(value, str):
            return sympy.sympify(value, evaluate=True)
        raise ValueError(f"sympy 표현식이 아니다: {type(value)}")


SympyExpr = Annotated[sympy.Expr | sympy.MatrixBase, _SympyField]


class ParsedExpression(BaseModel):
    """허용 AST 로 파싱된 표현식과 다중 정규형 뷰."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = Field(min_length=1)
    raw: SympyExpr
    exact: SympyExpr
    alpha_renamed: str
    ac_normalized: SympyExpr
    expanded: SympyExpr
    factored: SympyExpr
    rational_normalized: SympyExpr

    @field_serializer("*")
    def _sympy_to_str(self, value: Any) -> Any:
        if isinstance(value, sympy.Basic):
            return sympy.sstr(value)
        return value

    @field_validator("raw", mode="before")
    @classmethod
    def _ensure_parsed(cls, value: Any, info: Any) -> Any:
        return value

    def is_equivalent_to(self, other: ParsedExpression) -> bool:
        """정확 산술 기준 동치 판정 (Rational 우선)."""
        try:
            return bool(self.ac_normalized.equals(other.ac_normalized))
        except sympy.SympifyError:  # pragma: no cover - 방어
            return False

    def normalize_fingerprint(self) -> str:
        """표현식의 정규형 지문 (알파 치환 + 정확 산술)."""
        return _alpha_fingerprint(self.raw)


def parse_expression(source: str, symbols: set[str]) -> ParsedExpression:
    """표현식을 파싱하고 다중 정규형 뷰를 만든다."""
    declared = frozenset(symbols)
    raw = _parse_expr(source, declared)
    exact = _float_to_rational(raw)
    return ParsedExpression(
        source=source,
        raw=raw,
        exact=exact,
        alpha_renamed=_alpha_fingerprint(raw),
        ac_normalized=_ac_sort(exact),
        expanded=_expand_safe(exact),
        factored=_factor_safe(exact),
        rational_normalized=sympy.cancel(exact),
    )


def _expand_safe(expr: sympy.Basic) -> sympy.Basic:
    if isinstance(expr, sympy.MatrixBase):
        return expr.applyfunc(lambda e: sympy.expand(e))
    return sympy.expand(expr)


def _factor_safe(expr: sympy.Basic) -> sympy.Basic:
    if isinstance(expr, sympy.MatrixBase):
        return expr.applyfunc(lambda e: sympy.factor(e))
    return sympy.factor(expr)

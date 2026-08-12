"""T02.2 — SymPy 수식 파싱·다중 정규형·정의역 처리 테스트.

- T02.2-UT1: 1/2, 0.5, sqrt(4)/4 가 정확 산술 비교에서 동치다.
- T02.2-UT2: 변수명만 다른 동형 식이 같은 alpha-renamed 지문을 가진다.
- T02.2-UT3: 행렬곱·함수합성 순서는 정규화로 바뀌지 않는다.
- T02.2-UT4: 미선언 함수·임의 Python 표현은 파싱 단계에서 거부된다.
- T02.2-PT1: 임의 유효식의 정규화 전후가 정의역 안 표본에서 동치다.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from math_variant.errors import MathVariantError
from math_variant.math.expressions import parse_expression

_DECLARED = {"x", "y", "a", "b", "k", "m", "n", "t", "theta"}


def test_ut1_exact_arithmetic_equivalence() -> None:
    half = parse_expression("1/2", symbols=_DECLARED)
    point5 = parse_expression("0.5", symbols=_DECLARED)
    sqrt_over_4 = parse_expression("sqrt(4)/4", symbols=_DECLARED)

    assert half.alpha_renamed == point5.alpha_renamed
    assert half.ac_normalized == point5.ac_normalized
    assert half.is_equivalent_to(sqrt_over_4)
    assert half.expanded == sqrt_over_4.expanded


def test_ut2_alpha_rename_ignores_variable_names() -> None:
    # x^2 + 3x 와 y^2 + 3y 는 알파 치환 관점에서 같은 지문을 가진다.
    f_x = parse_expression("x**2 + 3*x", symbols=_DECLARED)
    f_y = parse_expression("y**2 + 3*y", symbols=_DECLARED)

    assert f_x.alpha_renamed == f_y.alpha_renamed
    # 단, raw 지문은 달라야 한다.
    assert f_x.raw != f_y.raw


def test_ut3_noncommutative_order_preserved() -> None:
    A = "Matrix([[1,2],[3,4]])"
    B = "Matrix([[0,1],[1,0]])"

    ab = parse_expression(f"({A}) * ({B})", symbols=_DECLARED)
    ba = parse_expression(f"({B}) * ({A})", symbols=_DECLARED)

    assert ab.ac_normalized != ba.ac_normalized
    assert ab.ac_normalized == ab.ac_normalized
    # 교환 정규화가 행렬곱 순서를 바꾸지 않았다: AB != BA 유지
    assert ab.expanded != ba.expanded


def test_ut4_undeclared_and_python_forms_rejected() -> None:
    for bad in ["os.system('id')", "__import__('os')", "cos(3)", "lambda x: x", "f(x)"]:
        try:
            parse_expression(bad, symbols=_DECLARED)
        except MathVariantError:
            continue
        else:  # pragma: no cover
            raise AssertionError(f"파싱이 거부되지 않았다: {bad}")


@given(
    a=st.integers(min_value=-20, max_value=20),
    b=st.integers(min_value=1, max_value=9),
)
@settings(max_examples=50, deadline=None)
def test_pt1_normalization_equivalent_in_domain(a: int, b: int) -> None:
    expr = f"({a}*x**2 + {b}*x + 1) * (x - 2)"
    parsed = parse_expression(expr, symbols=_DECLARED)

    x = parsed.raw.subs({"x": 3})
    expanded_x = parsed.expanded.subs({"x": 3})
    factored_x = parsed.factored.subs({"x": 3})

    assert parsed.ac_normalized.equals(parsed.expanded)
    assert parsed.ac_normalized.equals(parsed.factored)
    assert float(x) == float(expanded_x) == float(factored_x)


def test_parsed_expression_is_pydantic_serializable() -> None:
    parsed = parse_expression("x**2 + 1", symbols=_DECLARED)
    data = parsed.model_dump()
    assert data["raw"] == "x**2 + 1"
    assert "expanded" in data
    assert "factored" in data

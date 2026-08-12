"""도형의 방정식 결정론적 구조 추출기 (T02.4).

정규화 원문에서 지원 영역(좌표·직선·원·접선·이동·대칭)의
중심·반지름·직선·점·매개변수·목표·암묵 정의역을 규칙 기반으로 추출한다.

불확실성 처리:
- 추출할 수 없거나 모호하면 추측하지 않고 `unresolved_assumptions`를 만든다. (GT4)
- 범위 밖 개념(로그·집합 등)이 보이면 SCOPE_VIOLATION 을 발생시킨다. (GT3)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import cast

from math_variant.domain.problem import MathStatement, ProblemSpec
from math_variant.domain.scope import AnswerType, ScopeProfile
from math_variant.errors import ErrorCode, MathVariantError, StructuredError

_NUM = r"-?\d+(?:\.\d+)?"

_CIRCLE_STANDARD = re.compile(
    r"\(x\s*([+-])\s*(" + _NUM + r")\)\^2\s*\+\s*\(y\s*([+-])\s*(" + _NUM + r")\)\^2"
)
_RADIUS_AFTER = re.compile(r"=\s*([0-9a-zA-Z+\-*/^().]+(?:\s*[+-]\s*[0-9a-zA-Z]+)?)")
_CIRCLE_ORIGIN = re.compile(r"x\^2\s*\+\s*y\^2\s*=\s*([0-9a-zA-Z+\-*/^().]+)")
_POINT = re.compile(r"\(\s*(" + _NUM + r"),\s*(" + _NUM + r")\s*\)")
_POINT_NAMED = re.compile(r"([A-Z])\(\s*(" + _NUM + r"),\s*(" + _NUM + r")\s*\)")
_LINE_Y = re.compile(r"y\s*=\s*([+-]?[0-9]*)\s*([a-zA-Z])\s*(?:([+-])\s*([0-9a-zA-Z]+))?")
_LINE_STD = re.compile(
    r"([a-zA-Z])\s*x\s*([+-])\s*([a-zA-Z])\s*y\s*([+-])\s*([0-9a-zA-Z]+)\s*=\s*0"
)

_OUT_OF_SCOPE_KEYWORDS = [
    "로그",
    "지수",
    "집합",
    "명제",
    "역함수",
    "유리함수",
    "무리함수",
    "삼각함수",
    "수열",
    "벡터",
    "확률",
    "정적분",
    "미분",
    "적분",
]

_CONCEPT_HINTS = {
    "원": ["원", "x^2 + y^2", "x^2+y^2"],
    "직선": ["직선", "기울기", "절편"],
    "접선": ["접선"],
    "좌표": ["좌표"],
    "평행이동": ["평행이동"],
    "대칭이동": ["대칭이동"],
    "교점": ["교점", "만나"],
    "거리": ["거리", "둘레", "길이"],
    "중점": ["중점"],
}


@dataclass
class ExtractedShape:
    """추출된 원·직선·점 정보."""

    centers: list[tuple[str, str]] = field(default_factory=list)  # (cx, cy) 원의 중심
    given_center: tuple[str, str] | None = None
    given_center_label: str = ""
    passing_points: list[tuple[str, str]] = field(default_factory=list)
    circle_radius2: list[str] = field(default_factory=list)
    circle_literals: list[str] = field(default_factory=list)
    lines_y: list[tuple[str, str, str]] = field(default_factory=list)  # (m, sign, b)
    points: list[tuple[str, str]] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    goal: str = ""


class DeterministicSourceAnalyzer:
    """지원 도메인(도형의 방정식)에 대한 결정론적 구조 추출기."""

    def __init__(self, scope: ScopeProfile) -> None:
        self.scope = scope

    def analyze(self, normalized_text: str) -> ProblemSpec:
        text = self._normalize(normalized_text)
        self._check_out_of_scope(text)
        shape = self._extract(text)

        core_concepts = self._detect_concepts(text, shape)
        self._check_scope(core_concepts)

        givens = self._build_givens(shape)
        objective, answer_type, unknowns = self._build_goal(shape, text)
        implicit_domain = self._implicit_domain(shape, text)

        unresolved = self._detect_ambiguity(text, shape, givens, objective)

        return ProblemSpec(
            spec_id="auto",
            source_text=normalized_text,
            curriculum_version=self.scope.curriculum_version,
            exam_scope=list(self.scope.exam_scope),
            core_concepts=core_concepts,
            auxiliary_concepts=self._auxiliary_concepts(core_concepts),
            givens=givens,
            unknowns=unknowns,
            objective=objective,
            answer_type=cast(AnswerType, answer_type),
            explicit_assumptions=[],
            implicit_domain=implicit_domain,
            expected_methods=[],
            forbidden_knowledge=list(self.scope.forbidden_concepts),
            unresolved_assumptions=unresolved,
        )

    # --- 정규화 ---
    @staticmethod
    def _normalize(text: str) -> str:
        text = re.sub(r"<eq>|</eq>", "", text)
        text = text.replace("~", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _check_out_of_scope(self, text: str) -> None:
        for keyword in _OUT_OF_SCOPE_KEYWORDS:
            if keyword in text:
                raise MathVariantError(
                    StructuredError(
                        code=ErrorCode.SCOPE_VIOLATION,
                        message=f"범위 밖 개념 포함: {keyword}",
                        context={"concept": keyword, "profile": self.scope.profile_id},
                    )
                )

    # --- 추출 ---
    def _extract(self, text: str) -> ExtractedShape:
        shape = ExtractedShape()
        consumed_points: list[tuple[str, str]] = []

        # 명시적 중심 (중심 O(a,b) / 중심이 (a,b))
        for m in _POINT_NAMED.finditer(text):
            name, x, y = m.groups()
            if name == "O":
                shape.given_center = (x, y)
                shape.given_center_label = f"중심 O({x}, {y})"
                consumed_points.append((x, y))
        center_m = re.search(r"중심이\s*\(" + _NUM + r",\s*" + _NUM + r"\)", text)
        if center_m is not None:
            start = center_m.start()
            seg = text[start : center_m.end()]
            nums = re.findall(_NUM, seg)
            shape.given_center = (nums[0], nums[1]) if len(nums) >= 2 else None

        # 지나는 점 (한 점 (x,y)를 지나는 원) — 점 뒤를 확인
        for m in _POINT.finditer(text):
            x = m.group(1)
            y = m.group(2)
            after = text[m.end() : m.end() + 12]
            if (
                "지나는" in after
                or "지나" in after
                or "지나는" in text[max(0, m.start() - 12) : m.start()]
            ):
                shape.passing_points.append((x, y))
                consumed_points.append((x, y))

        # 방정식 형태의 원
        for m in _CIRCLE_STANDARD.finditer(text):
            sign_x, a, sign_y, b = m.groups()
            tail = text[m.end() :]
            rm = _RADIUS_AFTER.search(tail)
            r2 = rm.group(1).strip() if rm else "?"
            cx = a if sign_x == "-" else f"-{a}"
            cy = b if sign_y == "-" else f"-{b}"
            shape.centers.append((cx, cy))
            shape.circle_radius2.append(r2)
            shape.circle_literals.append(m.group(0))

        for m in _CIRCLE_ORIGIN.finditer(text):
            r2 = m.group(1)
            shape.centers.append(("0", "0"))
            shape.circle_radius2.append(r2)
            shape.circle_literals.append(m.group(0))

        # 일반 점 (중심·지나는 점 제외)
        for m in _POINT.finditer(text):
            pair = (m.group(1), m.group(2))
            if pair not in consumed_points:
                shape.points.append(pair)

        # 직선 y = mx + b
        for m in _LINE_Y.finditer(text):
            coeff, _var, sign, intercept = m.groups()
            slope = coeff if coeff not in ("", "+") else "1"
            if coeff == "-":
                slope = "-1"
            intercept_value = intercept if intercept is not None else "0"
            shape.lines_y.append((slope, sign or "+", intercept_value))
            if intercept is not None and not _is_number(intercept):
                shape.parameters.append(intercept)

        # 매개변수 후보 (도형·조건에 쓰인 한 글자)
        for token in re.findall(r"[a-zA-Z]", text):
            if token in {"x", "y", "O", "A", "B", "C", "P", "l", "m", "r", "N"}:
                continue
            shape.parameters.append(token)
        shape.parameters = sorted(set(shape.parameters))
        shape.goal = self._detect_goal(text)
        return shape

    @staticmethod
    def _detect_goal(text: str) -> str:
        for goal, keywords in [
            ("tangent", ["접선"]),
            ("no_intersection", ["만나지 않을", "범위를 구"]),
            ("reflection", ["대칭이동"]),
            ("translation", ["평행이동"]),
            ("coordinate", ["좌표를 구"]),
            ("intersection", ["교점", "만날 때"]),
            ("distance", ["거리의", "최솟값", "최댓값"]),
        ]:
            if any(k in text for k in keywords):
                return goal
        return ""

    # --- 개념 탐지 ---
    def _detect_concepts(self, text: str, shape: ExtractedShape) -> list[str]:
        concepts: list[str] = []
        for concept, hints in _CONCEPT_HINTS.items():
            if any(hint in text for hint in hints):
                concepts.append(concept)
        if shape.circle_literals and "원" not in concepts:
            concepts.append("원")
        return concepts

    def _check_scope(self, core_concepts: list[str]) -> None:
        unknown = [c for c in core_concepts if c not in self.scope.concept_vocabulary]
        if unknown:
            raise MathVariantError(
                StructuredError(
                    code=ErrorCode.SCOPE_VIOLATION,
                    message=f"범위 밖 핵심 개념: {unknown}",
                    context={"concepts": unknown, "profile": self.scope.profile_id},
                )
            )

    def _auxiliary_concepts(self, core_concepts: list[str]) -> list[str]:
        return [c for c in ["판별식", "거리", "좌표", "방정식"] if c not in core_concepts]

    # --- 주어진 정보 / 목표 ---
    def _build_givens(self, shape: ExtractedShape) -> list[MathStatement]:
        givens: list[MathStatement] = []
        if shape.given_center is not None:
            cx, cy = shape.given_center
            givens.append(
                MathStatement(
                    id="center",
                    natural_language=shape.given_center_label or f"중심 ({cx}, {cy})",
                )
            )
        for i, (x, y) in enumerate(shape.passing_points):
            givens.append(
                MathStatement(
                    id="passing_point" if i == 0 else f"passing_point{i + 1}",
                    natural_language=f"한 점 ({x}, {y})",
                )
            )
        for i, (x, y) in enumerate(shape.points):
            givens.append(
                MathStatement(
                    id="point" if i == 0 else f"point{i + 1}",
                    natural_language=f"점 ({x}, {y})",
                )
            )
        for i, ((cx, cy), r2) in enumerate(zip(shape.centers, shape.circle_radius2, strict=False)):
            if not shape.circle_literals:
                continue
            givens.append(
                MathStatement(
                    id="circle" if len(shape.circle_radius2) == 1 else f"circle{i + 1}",
                    natural_language=self._circle_natural(cx, cy, r2),
                    sympy_expr=f"(x - ({cx}))**2 + (y - ({cy}))**2 - ({r2})",
                )
            )
        for i, (m, sign, b) in enumerate(shape.lines_y):
            givens.append(
                MathStatement(
                    id="line" if len(shape.lines_y) == 1 else f"line{i + 1}",
                    natural_language=self._line_natural(m, sign, b),
                    sympy_expr=f"y - ({m})*x - ({b})",
                )
            )
        return givens

    @staticmethod
    def _center_display(cx: str, axis: str = "x") -> str:
        if cx == "0":
            return axis
        if cx.startswith("-"):
            return f"{axis} + {cx[1:]}"
        return f"{axis} - {cx}"

    def _circle_natural(self, cx: str, cy: str, r2: str) -> str:
        if cx == "0" and cy == "0":
            return f"원 x^2 + y^2 = {r2}"
        return (
            f"원 ({self._center_display(cx, 'x')})^2 + ({self._center_display(cy, 'y')})^2 = {r2}"
        )

    @staticmethod
    def _line_natural(m: str, sign: str, b: str) -> str:
        slope = "x" if m == "1" else ("-x" if m == "-1" else f"{m}x")
        if b == "0":
            return f"직선 y = {slope}"
        return f"직선 y = {slope} {sign} {b}"

    @staticmethod
    def _sign(value: str) -> str:
        if value.startswith("-"):
            return f"- {value[1:]}"
        return f"+ {value}"

    def _build_goal(self, shape: ExtractedShape, text: str) -> tuple[MathStatement, str, list[str]]:
        goal = shape.goal
        param = shape.parameters[0] if shape.parameters else ""
        if goal == "tangent":
            return (
                MathStatement(id="goal", natural_language="접선의 방정식을 구하시오"),
                "expression",
                [],
            )
        if goal == "no_intersection":
            return (
                MathStatement(
                    id="goal",
                    natural_language=f"실수 {param}의 범위를 구하시오"
                    if param
                    else "조건을 만족하는 값의 범위를 구하시오",
                ),
                "interval",
                list(shape.parameters),
            )
        if goal == "reflection":
            return (
                MathStatement(id="goal", natural_language="변환된 도형의 방정식을 구하시오"),
                "expression",
                [],
            )
        if goal == "translation":
            return (
                MathStatement(id="goal", natural_language="평행이동한 도형의 방정식을 구하시오"),
                "expression",
                [],
            )
        if goal == "coordinate":
            return (
                MathStatement(id="goal", natural_language="점의 좌표를 구하시오"),
                "coordinate",
                [],
            )
        if goal == "distance":
            return (
                MathStatement(id="goal", natural_language="거리의 최솟값을 구하시오"),
                "length",
                [],
            )
        return (
            MathStatement(id="goal", natural_language=text[:60]),
            "expression",
            list(shape.parameters),
        )

    def _implicit_domain(self, shape: ExtractedShape, text: str) -> list[str]:
        restrictions: list[str] = []
        for r2 in shape.circle_radius2:
            if _has_parameter(r2):
                restrictions.append(f"{r2} > 0")
        for m in re.finditer(r"sqrt\(\s*([^)]+)\)", text):
            radicand = m.group(1)
            if _has_parameter(radicand):
                restrictions.append(f"{radicand} >= 0")
        for m in re.finditer(r"1\s*/\s*\(([^)]+)\)", text):
            denom = m.group(1)
            if _has_parameter(denom):
                restrictions.append(f"{denom} != 0")
        return sorted(set(restrictions))

    def _detect_ambiguity(
        self,
        text: str,
        shape: ExtractedShape,
        givens: list[MathStatement],
        objective: MathStatement,
    ) -> list[str]:
        unresolved: list[str] = []
        if not givens:
            unresolved.append(
                "문제가 주어진 조건(원·직선·점)을 포함하지 않아 목표를 결정할 수 없다"
            )
        if not shape.circle_literals and not shape.lines_y and not shape.points:
            unresolved.append("지원 도메인(좌표·직선·원)의 구조를 추출할 수 없다")
        if len(objective.natural_language) < 6:
            unresolved.append("질문 목표가 모호하다")
        return unresolved


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _has_parameter(expr: str) -> bool:
    letters = set("abcdfghijklmnopqstuvwz")
    return any(ch in expr for ch in letters) and not all(
        ch in "x+ -*/^()0123456789." for ch in expr
    )

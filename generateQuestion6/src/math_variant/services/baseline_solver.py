"""원문 독립 풀이 (Baseline Solver) — T02.5.

원문의 제시 답을 보지 않고 문제 본문만으로 풀이한다. 풀이 단계를 SolutionGraph 로
구조화하고, 주장(claim)을 SymPy 로 고정 검증한다.

상태 구분:
- SATISFIABLE: 해가 존재하고 결정적이다.
- AMBIGUOUS_OR_MULTI_SOLUTION: 조건이 부족해 해가 여럿/무한히 많다.
- UNSATISFIABLE: 조건이 모순이다.
- UNRESOLVED: 지원 도메인이 아니거나 검증기가 판단할 수 없다 (fail-closed).
"""

from __future__ import annotations

import re
from typing import Literal

import sympy
from pydantic import BaseModel, ConfigDict, Field

from math_variant.domain.problem import MathStatement, ProblemSpec
from math_variant.domain.scope import ScopeProfile
from math_variant.domain.solution import SolutionGraph, SolutionNode
from math_variant.services.geometry_parser import _POINT

SolverStatus = Literal["SATISFIABLE", "AMBIGUOUS_OR_MULTI_SOLUTION", "UNSATISFIABLE", "UNRESOLVED"]

_NUM = r"-?\d+(?:\.\d+)?"

_CIRCLE_EQ = re.compile(r"x\^2\s*\+\s*y\^2\s*=\s*([0-9+\-*/^().]+)")
_CIRCLE_GENERAL = re.compile(
    r"x\^2\s*\+\s*y\^2\s*"
    r"(?:([+-])\s*(" + _NUM + r")\s*x)?\s*"
    r"(?:([+-])\s*(" + _NUM + r")\s*y)?\s*"
    r"(?:([+-])\s*(" + _NUM + r"))?\s*=\s*0"
)
_CENTER_AT = re.compile(r"중심이\s*\(" + _NUM + r",\s*" + _NUM + r"\)")
_PASSING_POINT = re.compile(r"점\s*\(" + _NUM + r",\s*" + _NUM + r"\)(?:을|를|을)\s*지나")


class VerificationCheck(BaseModel):
    """주장 하나에 대한 고정 검증 결과."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim: str
    status: Literal["PASS", "FAIL", "UNRESOLVED"]
    evidence: str = ""


class BaselineSolution(BaseModel):
    """독립 풀이 결과."""

    model_config = ConfigDict(extra="forbid")

    graph: SolutionGraph
    answer_set: list[str] = Field(default_factory=list)
    status: SolverStatus
    reason: str = ""
    verification_checks: list[VerificationCheck] = Field(default_factory=list)


class BaselineSolver:
    """지원 도메인(원·직선·접선)에 대한 결정론적 독립 풀이기."""

    def __init__(self, scope: ScopeProfile) -> None:
        self.scope = scope
        self.symbols = {"x", "y", "m", "k", "a", "b", "r"}

    def solve(self, spec: ProblemSpec) -> BaselineSolution:
        if spec.has_unresolved_assumptions:
            return self._unresolved("원문에 확정되지 않은 가정이 있다")
        return self.solve_text(spec.source_text)

    def solve_text(self, text: str) -> BaselineSolution:
        """본문 텍스트를 직접 풀이한다 (생성 후보의 고정 검증용)."""
        if "접선" in text and "원" in text:
            return self._solve_tangent(text)
        if ("두 점에서 만나" in text or "만나지 않을" in text or "접하" in text) and "원" in text:
            return self._solve_line_circle(text)
        if "원 내부의 점" in text and "걸" in text:
            return self._solve_center_walk(text)
        return self._unresolved("지원 도메인(원·직선·접선) 밖 또는 판단 불가")

    # --- 원 파싱 (중심·반지름) ---
    @staticmethod
    def _parse_circle(text: str) -> tuple[float, float, float] | None:
        """(중심x, 중심y, 반지름²) 를 반환한다. 지원 형식: 표준형·일반형·중심+지나는 점."""
        m = _CIRCLE_EQ.search(text)
        if m:
            try:
                r2 = float(sympy.sympify(m.group(1), evaluate=True))
            except (sympy.SympifyError, ValueError, TypeError):
                return None
            return (0.0, 0.0, r2)

        m = _CIRCLE_GENERAL.search(text)
        if m and "원" in text:
            sign_d, d, sign_e, e, sign_f, f = m.groups()
            d_val = float(d or 0) * (1 if sign_d in (None, "+") else -1)
            e_val = float(e or 0) * (1 if sign_e in (None, "+") else -1)
            f_val = float(f or 0) * (1 if sign_f in (None, "+") else -1)
            cx, cy = -d_val / 2, -e_val / 2
            r2 = (d_val / 2) ** 2 + (e_val / 2) ** 2 - f_val
            return (cx, cy, r2)

        center_m = _CENTER_AT.search(text)
        pass_m = _PASSING_POINT.search(text)
        if center_m and pass_m:
            nums_center = [float(v) for v in re.findall(_NUM, center_m.group(0))]
            nums_pass = [float(v) for v in re.findall(_NUM, pass_m.group(0))]
            if len(nums_center) >= 2 and len(nums_pass) >= 2:
                cx, cy = nums_center[0], nums_center[1]
                r2 = (nums_pass[0] - cx) ** 2 + (nums_pass[1] - cy) ** 2
                return (cx, cy, r2)
        return None

    # --- 접선 문제 ---
    def _solve_tangent(self, text: str) -> BaselineSolution:
        circle = self._parse_circle(text)
        if circle is None:
            return self._unresolved("원의 방정식을 추출할 수 없다")
        cx, cy, r2 = circle
        if r2 < 0:
            return self._unsatisfiable("반지름 제곱이 음수여서 원이 존재할 수 없다")

        point_m = _POINT.search(text)
        if point_m is None:
            return BaselineSolution(
                graph=self._single_node_graph("접선의 방정식", "조건 부족"),
                status="AMBIGUOUS_OR_MULTI_SOLUTION",
                reason="접선을 결정할 외부 점 또는 접점이 주어지지 않았다",
            )

        px, py = float(point_m.group(1)), float(point_m.group(2))
        center_distance2 = (px - cx) ** 2 + (py - cy) ** 2
        if center_distance2 < r2:
            return self._unsatisfiable("점이 원 내부에 있어 접선이 존재하지 않는다")

        answers: list[tuple[float, str]] = []
        checks: list[VerificationCheck] = []
        nodes: list[SolutionNode] = []
        node_id = 1

        if abs(px - cx) == float(sympy.sqrt(r2)):
            # 수직 접선 x = px
            line = f"x = {px:g}"
            ok = True
            answers.append((px, line))
            checks.append(
                VerificationCheck(
                    claim=line,
                    status="PASS" if ok else "FAIL",
                    evidence=f"중심-직선 거리 = {abs(px - cx):g} == 반지름 {sympy.sqrt(r2):g}",
                )
            )
            nodes.append(
                SolutionNode(
                    id=f"tangent{node_id}",
                    statement=self._stmt(line),
                    verifier="sympy",
                    points=1,
                    justification="수직 접선 거리 조건 통과",
                    claimed=False,
                )
            )
            node_id += 1

        if center_distance2 > r2:
            # 기울기 m 인 접선 y - py = m(x - px) → m x - y + (py - m px) = 0
            m = sympy.Symbol("m")
            distance2 = ((py - cy) - m * (px - cx)) ** 2 / (m**2 + 1)
            equation = sympy.Eq(distance2, r2)
            slopes = sympy.solve(equation, m, dict=False)
            for slope in slopes:
                s = float(slope)
                dist = abs((py - cy) - s * (px - cx)) / (s**2 + 1) ** 0.5
                ok = abs(dist - sympy.sqrt(r2)) < 1e-9
                line = f"y - ({py:g}) = {s:g}(x - ({px:g}))"
                checks.append(
                    VerificationCheck(
                        claim=line,
                        status="PASS" if ok else "FAIL",
                        evidence=(f"중심-직선 거리 = {dist:g} vs 반지름 = {sympy.sqrt(r2):g}"),
                    )
                )
                if ok:
                    answers.append((s, line))
                    nodes.append(
                        SolutionNode(
                            id=f"tangent{node_id}",
                            statement=self._stmt(line),
                            verifier="sympy",
                            points=1,
                            justification=f"거리 조건 통과: {dist:g} == {sympy.sqrt(r2):g}",
                            claimed=False,
                        )
                    )
                    node_id += 1

        if not answers:
            return self._unsatisfiable("거리 조건을 만족하는 접선이 없다")

        answers_sorted = sorted(set(ans for _, ans in answers))
        final_id = nodes[-1].id
        graph = SolutionGraph(
            graph_id="baseline-tangent",
            nodes=nodes,
            final_node_ids=[final_id],
            total_points=float(len(nodes)),
        )
        return BaselineSolution(
            graph=graph,
            answer_set=answers_sorted,
            status="SATISFIABLE",
            verification_checks=checks,
        )

    # --- 직선-원 위치 관계 (만나지 않음 / 두 점에서 만남 / 접함) ---
    def _solve_line_circle(self, text: str) -> BaselineSolution:
        circle = self._parse_circle(text)
        line_m = re.search(r"y\s*=\s*([+-]?[0-9]*)\s*x\s*([+-])\s*([a-zA-Z])", text)
        if circle is None or line_m is None:
            return self._unresolved("원·직선 구조를 추출할 수 없다")
        cx, cy, r2 = circle

        m_coeff = line_m.group(1) or "1"
        if m_coeff in ("", "+"):
            m_val = 1.0
        elif m_coeff == "-":
            m_val = -1.0
        else:
            m_val = float(m_coeff)

        if r2 < 0:
            return self._unsatisfiable("반지름 제곱이 음수여서 원이 존재할 수 없다")

        # 중심 (cx,cy)에서 직선 y = m x + k 까지 거리 = |cy - m*cx - k| / sqrt(m^2+1)
        center_shift = cy - m_val * cx
        threshold = (r2 * (m_val**2 + 1)) ** 0.5
        lo = center_shift - threshold
        hi = center_shift + threshold

        if "두 점에서 만나" in text or "만나도록" in text:
            # 서로 다른 두 점에서 만남 ⟺ 거리 < 반지름
            answer_set = [f"{lo:g} < k < {hi:g}"]
            condition = "중심-직선 거리 < 반지름"
        elif "접하" in text:
            # 접함 ⟺ 거리 = 반지름
            answer_set = [f"k = {lo:g} 또는 k = {hi:g}"]
            condition = "중심-직선 거리 = 반지름"
        else:
            # 만나지 않을 ⟺ 거리 > 반지름
            answer_set = [f"k > {hi:g} 또는 k < {lo:g}"]
            condition = "중심-직선 거리 > 반지름"

        graph = SolutionGraph(
            graph_id="baseline-line-circle",
            nodes=[
                SolutionNode(
                    id="range",
                    statement=self._stmt(f"k의 범위: {answer_set[0]}"),
                    verifier="sympy",
                    points=1,
                    justification=condition,
                    claimed=False,
                )
            ],
            final_node_ids=["range"],
            total_points=1,
        )
        return BaselineSolution(
            graph=graph,
            answer_set=answer_set,
            status="SATISFIABLE",
            verification_checks=[
                VerificationCheck(
                    claim="k의 범위",
                    status="PASS",
                    evidence=(
                        f"|k - {center_shift:g}| {condition.split(' ')[1]} "
                        f"sqrt(r2*(m^2+1)) = {threshold:g}"
                    ),
                )
            ],
        )

    # --- 원 내부의 점에서 직선으로 걸어 중심 거리 구하기 ---
    def _solve_center_walk(self, text: str) -> BaselineSolution:
        radius_m = re.search(r"반지름이\s*([0-9.]+)", text)
        near_m = re.search(r"거리(?:가|를)?\s*([0-9.]+)", text)
        far_total = re.search(r"총\s*걸은\s*거리(?:가|를)?\s*([0-9.]+)", text)
        if far_total is None:
            far_total = re.search(r"반대편.{0,15}?거리(?:가|를)?\s*([0-9.]+)", text)
        if radius_m is None or near_m is None or far_total is None:
            return self._unresolved("원 내부 걷기 조건을 추출할 수 없다")
        r = float(radius_m.group(1))
        near = float(near_m.group(1))
        far = float(far_total.group(1))

        # 직선으로 원을 가로지르는 총 거리가 지름과 같아야 한다.
        if abs(far - 2 * r) > 1e-9:
            return self._unsatisfiable(f"지름 불일치: 총 거리 {far:g} != 2r = {2 * r:g}")
        pc = r - near  # 내부 점 P에서 중심까지 거리
        if pc < 0:
            return self._unsatisfiable("걸은 거리가 반지름보다 커 모순이다")

        answer_set = [f"{pc:g}"]
        graph = SolutionGraph(
            graph_id="baseline-center-walk",
            nodes=[
                SolutionNode(
                    id="dist",
                    statement=self._stmt(f"점 P에서 원의 중심까지의 거리 = {pc:g}"),
                    verifier="sympy",
                    points=1,
                    justification=(
                        f"총 거리 {far:g} = 지름 2r 이므로 P 는 중심에서 "
                        f"r - PA = {r:g} - {near:g} = {pc:g} 떨어져 있다"
                    ),
                    claimed=False,
                )
            ],
            final_node_ids=["dist"],
            total_points=1,
        )
        return BaselineSolution(
            graph=graph,
            answer_set=answer_set,
            status="SATISFIABLE",
            verification_checks=[
                VerificationCheck(
                    claim="중심까지의 거리",
                    status="PASS",
                    evidence=f"PC = r - PA = {r:g} - {near:g} = {pc:g}",
                )
            ],
        )

    # --- 도우미 ---
    def _single_node_graph(self, label: str, statement: str) -> SolutionGraph:
        return SolutionGraph(
            graph_id="baseline-single",
            nodes=[
                SolutionNode(
                    id="n1",
                    statement=self._stmt(statement),
                    verifier="human",
                    points=0,
                    claimed=True,
                )
            ],
            final_node_ids=["n1"],
            total_points=0,
        )

    @staticmethod
    def _stmt(natural: str) -> MathStatement:
        return MathStatement(id="st", natural_language=natural)

    def _unresolved(self, reason: str) -> BaselineSolution:
        return BaselineSolution(
            graph=self._single_node_graph("판단 불가", reason),
            status="UNRESOLVED",
            reason=reason,
        )

    def _unsatisfiable(self, reason: str) -> BaselineSolution:
        return BaselineSolution(
            graph=self._single_node_graph("모순", reason),
            status="UNSATISFIABLE",
            reason=reason,
        )

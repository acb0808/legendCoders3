"""T02.5 — 실제 시험지 원문에 대한 Baseline Solver 통합 테스트."""

from __future__ import annotations

import json
import re
from pathlib import Path

from math_variant.domain.problem import MathStatement, ProblemSpec
from math_variant.domain.scope import ScopeProfile
from math_variant.services.baseline_solver import BaselineSolver
from math_variant.services.normalize import normalize_source
from math_variant.verifiers.source_gate import SourceGate, SourceGateStatus

_SCOPE = ScopeProfile(
    profile_id="p1",
    school_name="광문고",
    exam_scope=["도형의 방정식"],
    allowed_units=["원의 방정식"],
    concept_vocabulary=["원", "직선", "접선", "좌표", "교점"],
    allowed_answer_types=["expression"],
)


def _find_question(testpaper_dir: Path, source: str, number: str) -> dict:
    path = testpaper_dir / source
    questions = json.loads(path.read_text(encoding="utf-8"))
    for question in questions:
        if str(question["question_number"]) == number:
            return question
    raise AssertionError(f"질문을 찾지 못함: {source} #{number}")


def _normalize(text: str) -> str:
    text = re.sub(r"<eq>|</eq>", "", text)
    text = text.replace("~", " ")
    return re.sub(r"\s+", " ", text).strip()


def test_real_tangent_problem_passes_gate(testpaper_dir: Path) -> None:
    """[2018] 광문고 Q21 — 원문 제공 답(두 접선)과 독립 풀이가 일치해 PASS 가 된다."""
    question = _find_question(
        testpaper_dir, "[2018년 기출] 광문고1-2 중간 (주)_structured.json", "21"
    )
    text = normalize_source(question["question_text"])
    assert "접선" in text and "원" in text

    spec = ProblemSpec(
        spec_id="s",
        source_text=text,
        curriculum_version="2022 개정",
        exam_scope=["도형의 방정식"],
        core_concepts=["원", "접선"],
        givens=[],
        objective=MathStatement(id="goal", natural_language="접선의 방정식을 구하시오"),
        answer_type="expression",
        unresolved_assumptions=[],
    )
    baseline = BaselineSolver(_SCOPE).solve(spec)
    result = SourceGate().evaluate(spec, baseline)

    assert result.status == SourceGateStatus.PASS, result.reason
    assert len(baseline.answer_set) == 2

"""T01.2 — 상태 머신·ProblemSpec·SolutionGraph 불변식 테스트."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from math_variant.domain.problem import MathStatement, ProblemSpec
from math_variant.domain.run import GenerationRun, RunState
from math_variant.domain.solution import SolutionGraph, SolutionNode


def _spec(unresolved: list[str] | None = None) -> ProblemSpec:
    return ProblemSpec(
        spec_id="s1",
        source_text="원 x^2+y^2=4 에 점 (1,2) 에서 그은 접선의 방정식을 구하시오.",
        curriculum_version="2022 개정",
        exam_scope=["도형의 방정식"],
        core_concepts=["원과 접선"],
        objective=MathStatement(id="goal", natural_language="접선 방정식"),
        answer_type="expression",
        unresolved_assumptions=unresolved or [],
    )


def test_unresolved_assumptions_block_auto_generation() -> None:
    assert _spec(unresolved=["원의 중심 좌표 미지정"]).has_unresolved_assumptions is True
    assert _spec().has_unresolved_assumptions is False


def test_state_machine_forward_only() -> None:
    run = GenerationRun(run_id="r1", source_ref="src")
    run.transition(RunState.NORMALIZED)
    run.transition(RunState.ANALYZED)
    assert run.state == RunState.ANALYZED

    with pytest.raises(ValueError):
        run.transition(RunState.NORMALIZED)


def test_gate_transition_requires_evidence() -> None:
    run = GenerationRun(run_id="r2", source_ref="src")
    with pytest.raises(ValueError, match="fail-closed"):
        run.gate_transition(RunState.IR_COMPILED, evidence_ok=False)


def test_solution_graph_point_consistency() -> None:
    with pytest.raises(ValidationError):
        SolutionGraph(
            graph_id="g1",
            nodes=[SolutionNode(id="n1", statement=_spec().objective, points=2)],
            final_node_ids=["n1"],
            total_points=5,
        )


def test_final_node_must_exist() -> None:
    with pytest.raises(ValidationError):
        SolutionGraph(
            graph_id="g2",
            nodes=[SolutionNode(id="n1", statement=_spec().objective, points=2)],
            final_node_ids=["n2"],
            total_points=2,
        )

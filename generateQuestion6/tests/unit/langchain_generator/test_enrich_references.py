"""단위 테스트 — LangGraph enrich_references 노드 동작 검증 (M4 TDD)."""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.runnables import RunnableParallel

from math_variant.agents.schemas import PlannerOutput, ProductionStrategy
from math_variant.langchain_generator.pipeline import (
    EventEmitter,
    PipelineContext,
    _enrich_references_node,
)
from math_variant.reference.condition_retriever import ConditionStyleRetriever
from math_variant.reference.exam_retriever import ExamPatternRetriever
from math_variant.reference.sections import build_reference_runnable
from math_variant.reference.style_retriever import SolutionStyleRetriever


def test_enrich_references_node_with_runnable(tmp_path: Path) -> None:
    """reference_runnable이 있을 때 상태 채널에 참조 객체 및 섹션 문자열이 저장되는지 검증."""
    exam_path = tmp_path / "reference_exam_patterns.jsonl"
    exam_card = {
        "topic_id": "C08-01-03-01",
        "unit": "원의 방정식",
        "pattern": "원",
        "wording": "구하시오",
        "condition_style": ["원 _"],
        "example_abstract": "원",
        "difficulty_zone": "중",
        "source_count": 1,
        "sources": [],
    }
    with open(exam_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(exam_card) + "\n")

    cond_path = tmp_path / "condition_style_index.json"
    cond_data = {
        "C08-01-03-01": {
            "topic_id": "C08-01-03-01",
            "unit": "원의 방정식",
            "condition_phrasings": [{"pattern": "원 _", "freq": 3}],
            "wording_conventions": ["구하시오"],
        }
    }
    with open(cond_path, "w", encoding="utf-8") as f:
        json.dump(cond_data, f)

    style_path = tmp_path / "solution_style_guide.json"
    style_data = {
        "원의 방정식": {
            "unit": "원의 방정식",
            "style": {
                "open": "열기",
                "transform_order": ["순서"],
                "justification_vocab": ["따라서"],
                "close": "닫기",
                "sample_step": "예시",
            },
        }
    }
    with open(style_path, "w", encoding="utf-8") as f:
        json.dump(style_data, f)

    exam_retriever = ExamPatternRetriever(index_path=exam_path, k=3)
    cond_retriever = ConditionStyleRetriever(index_path=cond_path, k=5)
    style_retriever = SolutionStyleRetriever(index_path=style_path)
    runnable = build_reference_runnable(exam_retriever, cond_retriever, style_retriever)

    class DummyRuntime:
        def __init__(self, ref_runnable: RunnableParallel) -> None:
            self.context = PipelineContext(
                planner=None,  # type: ignore[arg-type]
                ideator=None,  # type: ignore[arg-type]
                selector=None,  # type: ignore[arg-type]
                generator=None,  # type: ignore[arg-type]
                code_reviewer=None,  # type: ignore[arg-type]
                critic=None,  # type: ignore[arg-type]
                judge=None,  # type: ignore[arg-type]
                vision=None,
                sandbox=None,  # type: ignore[arg-type]
                blind_solvers=None,  # type: ignore[arg-type]
                runs_dir=tmp_path,
                ideator_count=3,
                max_refine=2,
                emit=EventEmitter(None),
                reference_runnable=ref_runnable,
            )

    planner_out = PlannerOutput(
        core_concepts=["C08-01-03-01", "원의 방정식"],
        objective="구하시오",
        answer_type="expression",
        domain="도형의 방정식",
        preservation_goals=["성질"],
        forbidden_structure=["골격"],
        strategy=ProductionStrategy(
            difficulty_target="중",
            preservation_goals=["성질"],
            variation_direction=["변형"],
            quality_criteria=["기준"],
        ),
    )

    state = {"planner_out": planner_out}
    runtime = DummyRuntime(runnable)
    res = _enrich_references_node(state, runtime)  # type: ignore[arg-type]

    assert len(res["exam_patterns"]) == 1
    assert len(res["condition_refs"]) == 1
    assert res["style_guide"] is not None
    assert "[기출 출제 패턴 참조" in res["pattern_section"]
    assert "[조건 표현 관례 참조]" in res["condition_section"]
    assert "[해설 스타일 가이드 (원의 방정식)]" in res["style_section"]

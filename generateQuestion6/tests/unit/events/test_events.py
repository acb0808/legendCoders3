"""웹 생성 워크플로 — 진행 이벤트 모델·요약 테스트."""

from __future__ import annotations

from datetime import UTC, datetime

from math_variant.events import (
    ROLE_TO_STAGE,
    EventStage,
    PipelineEvent,
    summarize_response,
)


def test_stage_event_roundtrip() -> None:
    event = PipelineEvent(
        event_id="evt-1",
        type="stage",
        stage=EventStage.PLANNER,
        status="started",
        message="기획 시작",
        ts=datetime.now(UTC),
    )
    dumped = event.model_dump(mode="json")
    assert dumped["stage"] == "planner"
    assert dumped["type"] == "stage"
    restored = PipelineEvent.model_validate(dumped)
    assert restored.message == "기획 시작"


def test_llm_call_event_roundtrip() -> None:
    event = PipelineEvent(
        event_id="evt-2",
        type="llm_call",
        stage=EventStage.IDEATION,
        status="done",
        message="",
        ts=datetime.now(UTC),
        data={
            "role": "ideator",
            "schema": "IdeationOutput",
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "temperature": 1.4,
            "attempts": 1,
            "latency_ms": 4231,
            "cost_usd": 0.0021,
            "ok": True,
            "summary": {"idea_id": "idea-0", "title": "질문 역전"},
        },
    )
    assert event.model_dump(mode="json")["data"]["provider"] == "deepseek"


def test_role_to_stage_mapping() -> None:
    assert ROLE_TO_STAGE["planner"] == EventStage.PLANNER
    assert ROLE_TO_STAGE["ideator"] == EventStage.IDEATION
    assert ROLE_TO_STAGE["generator"] == EventStage.GENERATION
    assert ROLE_TO_STAGE["blind_solver"] == EventStage.BLIND
    assert ROLE_TO_STAGE["vision"] == EventStage.GENERATION


def test_summarize_known_schemas() -> None:
    assert summarize_response("IdeationOutput", {"idea_id": "i1", "title": "질문 역전"}) == {
        "idea_id": "i1",
        "title": "질문 역전",
    }
    assert summarize_response("GeneratorOutput", {"final_answer_claim": "8sqrt(2)"}) == {
        "final_answer_claim": "8sqrt(2)"
    }
    assert summarize_response("CodeReviewOutput", {"verdict": "APPROVE", "safe": True}) == {
        "verdict": "APPROVE"
    }


def test_summarize_unknown_schema_returns_scalar_keys() -> None:
    assert summarize_response("UnknownSchema", {"x": 1, "problem_text": "본문"}) == {
        "problem_text": "본문"
    }

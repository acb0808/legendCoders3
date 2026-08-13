"""T08 — 엔진이 LLM 호출 이벤트를 방출하는지 테스트."""

from __future__ import annotations

from math_variant.events import EventStage, PipelineEvent
from math_variant.providers.contracts import (
    ProviderErrorCode,
    RolePolicy,
    StructuredRequest,
)
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine


class _Provider:
    name = "fake"

    def complete(self, prompt, policy):
        return type(
            "Completion",
            (),
            {
                "provider": "fake",
                "raw_text": (
                    '{"idea_id": "idea-0", "title": "질문 역전", '
                    '"preserved_concepts": ["원"], '
                    '"changed_dimensions": ["objective"], '
                    '"change_description": ["질문 방향 역전"], '
                    '"construction_blueprint": "조건과 결론을 뒤집는다"}'
                ),
                "latency_ms": 10,
                "cost_usd": 0.0,
            },
        )()


class _RaisingProvider:
    name = "fake"

    def complete(self, prompt, policy):
        raise RuntimeError("sk-ULTRA_SECRET_123 provider boom")


class _StreamingProvider:
    """on_delta 를 지원하는 공급자 — 토큰 조각을 콜백으로 전달한다."""

    name = "fake"

    def complete(self, prompt, policy, on_delta=None):
        if on_delta is not None:
            on_delta("", "We need to keep the original concept.")
            on_delta('{"idea_id": "idea-0", "title": "질문 역전", ', "")
            on_delta(
                '"preserved_concepts": ["원"], "changed_dimensions": ["objective"]}',
                "",
            )
        return type(
            "Completion",
            (),
            {
                "provider": "fake",
                "raw_text": (
                    '{"idea_id": "idea-0", "title": "질문 역전", '
                    '"preserved_concepts": ["원"], '
                    '"changed_dimensions": ["objective"], '
                    '"change_description": ["질문 방향 역전"], '
                    '"construction_blueprint": "조건과 결론을 뒤집는다"}'
                ),
                "latency_ms": 10,
                "cost_usd": 0.0,
            },
        )()


def test_engine_emits_llm_call_event() -> None:
    from math_variant.agents.schemas import register_agent_schemas

    schemas = SchemaRegistry()
    register_agent_schemas(schemas)
    emitted: list[PipelineEvent] = []
    engine = StructuredOutputEngine(
        primary=None, fallback=None, schemas=schemas, on_event=emitted.append
    )
    engine.role_resolver = _FakeResolver()

    response = engine.generate_structured(
        StructuredRequest(
            request_id="ideator-0",
            role=RolePolicy.IDEATOR,
            prompt="p",
            response_schema="IdeationOutput",
        ),
        policy=None,
    )
    assert response.ok
    assert len(emitted) == 1
    event = emitted[0]
    assert event.type == "llm_call"
    assert event.stage == EventStage.IDEATION
    assert event.data["provider"] == "fake"
    assert event.data["schema"] == "IdeationOutput"
    assert event.data["ok"] is True
    assert event.data["summary"] == {
        "idea_id": "idea-0",
        "title": "질문 역전",
        "changed_dimensions": ["objective"],
    }


def test_engine_emits_failed_event_when_provider_raises() -> None:
    from math_variant.agents.schemas import register_agent_schemas

    schemas = SchemaRegistry()
    register_agent_schemas(schemas)
    emitted: list[PipelineEvent] = []
    engine = StructuredOutputEngine(
        primary=None, fallback=None, schemas=schemas, on_event=emitted.append
    )
    engine.role_resolver = _FakeResolver(provider=_RaisingProvider())

    response = engine.generate_structured(
        StructuredRequest(
            request_id="ideator-fail",
            role=RolePolicy.IDEATOR,
            prompt="p",
            response_schema="IdeationOutput",
        ),
        policy=None,
    )
    assert not response.ok
    assert response.error is not None
    assert response.error.code == ProviderErrorCode.INFRA_ERROR
    assert len(emitted) == 1
    event = emitted[0]
    assert event.type == "llm_call"
    assert event.status == "failed"
    assert event.data["ok"] is False
    assert isinstance(event.data["error"], dict)
    assert "code" in event.data["error"]
    assert event.data["error"]["code"] == "INFRA_ERROR"
    assert "sk-ULTRA" not in event.data["error"]["detail"]
    assert event.data["summary"] == {}


def test_engine_without_on_event_still_works() -> None:
    from math_variant.agents.schemas import register_agent_schemas

    schemas = SchemaRegistry()
    register_agent_schemas(schemas)
    engine = StructuredOutputEngine(primary=None, fallback=None, schemas=schemas)
    engine.role_resolver = _FakeResolver()
    response = engine.generate_structured(
        StructuredRequest(
            request_id="r",
            role=RolePolicy.IDEATOR,
            prompt="p",
            response_schema="IdeationOutput",
        ),
        policy=None,
    )
    assert response.ok


def test_engine_emits_llm_delta_events_from_streaming_provider() -> None:
    from math_variant.agents.schemas import register_agent_schemas

    schemas = SchemaRegistry()
    register_agent_schemas(schemas)
    emitted: list[PipelineEvent] = []
    engine = StructuredOutputEngine(
        primary=None, fallback=None, schemas=schemas, on_event=emitted.append
    )
    engine.role_resolver = _FakeResolver(provider=_StreamingProvider())

    response = engine.generate_structured(
        StructuredRequest(
            request_id="ideator-stream",
            role=RolePolicy.IDEATOR,
            prompt="p",
            response_schema="IdeationOutput",
        ),
        policy=None,
    )
    assert response.ok
    delta_events = [e for e in emitted if e.type == "llm_delta"]
    call_events = [e for e in emitted if e.type == "llm_call"]
    assert len(delta_events) == 3
    assert delta_events[0].status == "streaming"
    assert delta_events[0].data["role"] == "ideator"
    assert delta_events[0].data["reasoning"] == "We need to keep the original concept."
    assert delta_events[0].data["attempt"] == 1
    assert delta_events[1].data["content"].startswith('{"idea_id"')
    assert call_events[0].data["summary"]["title"] == "질문 역전"


def test_engine_falls_back_when_provider_rejects_on_delta() -> None:
    """on_delta 를 지원하지 않는 공급자(구형 fake)는 TypeError 로 감지해 비스트리밍 호출한다."""
    from math_variant.agents.schemas import register_agent_schemas

    schemas = SchemaRegistry()
    register_agent_schemas(schemas)
    emitted: list[PipelineEvent] = []
    engine = StructuredOutputEngine(
        primary=None, fallback=None, schemas=schemas, on_event=emitted.append
    )
    engine.role_resolver = _FakeResolver()

    response = engine.generate_structured(
        StructuredRequest(
            request_id="ideator-legacy",
            role=RolePolicy.IDEATOR,
            prompt="p",
            response_schema="IdeationOutput",
        ),
        policy=None,
    )
    assert response.ok
    assert all(e.type != "llm_delta" for e in emitted)
    assert any(e.type == "llm_call" and e.data["ok"] for e in emitted)


class _FakeResolver:
    def __init__(self, provider=None) -> None:
        self._provider = provider or _Provider()

    def provider_for(self, role: RolePolicy):
        return self._provider

    def fallback_for(self, role: RolePolicy):
        return None

    def policy_for(self, role: RolePolicy):
        return type(
            "Policy",
            (),
            {
                "provider": "fake",
                "model": "fake-model",
                "max_tokens": 100,
            },
        )()

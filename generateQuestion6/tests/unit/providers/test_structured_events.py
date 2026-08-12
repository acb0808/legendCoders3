"""T08 — 엔진이 LLM 호출 이벤트를 방출하는지 테스트."""

from __future__ import annotations

from math_variant.events import EventStage, PipelineEvent
from math_variant.providers.contracts import RolePolicy, StructuredRequest
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


class _FakeResolver:
    def provider_for(self, role: RolePolicy):
        return _Provider()

    def fallback_for(self, role: RolePolicy):
        return None

    def policy_for(self, role: RolePolicy):
        return type(
            "Policy",
            (),
            {
                "provider": "fake",
                "model": "fake-model",
                "temperature": 0.2,
                "max_tokens": 100,
            },
        )()

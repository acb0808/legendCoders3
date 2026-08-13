"""LangChainRoleEngine 단위 테스트 — 재시도·복구·비용 계측 및 이벤트 발행 검증."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from math_variant.events import PipelineEvent
from math_variant.langchain_generator.engine import LangChainRoleEngine
from math_variant.providers.contracts import (
    ProviderErrorCode,
    RolePolicy,
    StructuredRequest,
)


class DummyOutput(BaseModel):
    title: str
    value: int


def _make_raw_output(
    parsed: Any,
    total_tokens: int = 1500,
    model_name: str = "deepseek-flash",
    parsing_error: Any = None,
) -> dict[str, Any]:
    raw_msg = AIMessage(
        content="{}",
        usage_metadata={"total_tokens": total_tokens, "input_tokens": 1000, "output_tokens": 500},
        response_metadata={"model_name": model_name, "token_usage": {"total_tokens": total_tokens}},
    )
    return {"raw": raw_msg, "parsed": parsed, "parsing_error": parsing_error}


def test_engine_success_with_cost_and_event() -> None:
    events: list[PipelineEvent] = []
    dummy = DummyOutput(title="test", value=42)

    def _invoke(_payload: dict[str, str]) -> Any:
        return _make_raw_output(dummy, total_tokens=2000, model_name="deepseek-v4-flash")

    engine = LangChainRoleEngine(
        chains={RolePolicy.PLANNER: RunnableLambda(_invoke)},
        on_event=events.append,
    )

    req = StructuredRequest(
        request_id="req-1",
        role=RolePolicy.PLANNER,
        prompt="hello",
        response_schema="dummy",
    )
    resp = engine.generate_structured(req, None)

    assert resp.ok is True
    assert resp.data == {"title": "test", "value": 42}
    assert resp.attempts == 1
    assert resp.cost_usd == 0.002  # 2000 / 1_000_000
    assert resp.provider == "deepseek-v4-flash"
    assert resp.latency_ms >= 0

    assert len(events) == 1
    assert events[0].type == "llm_call"
    assert events[0].data["ok"] is True
    assert events[0].data["cost_usd"] == 0.002


def test_engine_transient_retry_success() -> None:
    call_count = 0
    dummy = DummyOutput(title="recovered", value=100)

    def _invoke(_payload: dict[str, str]) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("network glitch (empty response)")
        return _make_raw_output(dummy, total_tokens=1000)

    engine = LangChainRoleEngine(
        chains={RolePolicy.IDEATOR: RunnableLambda(_invoke)},
        max_transient_retries=5,
    )

    req = StructuredRequest(
        request_id="req-2",
        role=RolePolicy.IDEATOR,
        prompt="ideate",
        response_schema="dummy",
    )
    resp = engine.generate_structured(req, None)

    assert resp.ok is True
    assert resp.attempts == 3
    assert call_count == 3
    assert resp.data["title"] == "recovered"


def test_engine_schema_repair_success() -> None:
    prompts_received: list[str] = []
    dummy = DummyOutput(title="repaired", value=99)

    def _invoke(payload: dict[str, str]) -> Any:
        prompt = payload["input"]
        prompts_received.append(prompt)
        if len(prompts_received) == 1:
            # 1회차: 파싱 에러 반환
            return _make_raw_output(parsed=None, parsing_error="Invalid JSON structure")
        # 2회차: 복구 프롬프트 수신 후 성공
        return _make_raw_output(parsed=dummy)

    engine = LangChainRoleEngine(
        chains={RolePolicy.GENERATOR: RunnableLambda(_invoke)},
        max_repair_attempts=1,
    )

    req = StructuredRequest(
        request_id="req-3",
        role=RolePolicy.GENERATOR,
        prompt="generate candidate",
        response_schema="dummy",
    )
    resp = engine.generate_structured(req, None)

    assert resp.ok is True
    assert resp.attempts == 2
    assert len(prompts_received) == 2
    assert "[시스템] 이전 응답이 검증에 실패했습니다." in prompts_received[1]
    assert resp.data["title"] == "repaired"


def test_engine_fallback_chain_success() -> None:
    dummy_fallback = DummyOutput(title="from_fallback", value=777)

    def _primary_invoke(_payload: dict[str, str]) -> Any:
        raise RuntimeError("Primary API 500 Internal Error")

    def _fallback_invoke(_payload: dict[str, str]) -> Any:
        return _make_raw_output(dummy_fallback, model_name="gpt-5.6-luna")

    engine = LangChainRoleEngine(
        chains={RolePolicy.JUDGE: RunnableLambda(_primary_invoke)},
        fallback_chains={RolePolicy.JUDGE: RunnableLambda(_fallback_invoke)},
        max_transient_retries=0,
    )

    req = StructuredRequest(
        request_id="req-4",
        role=RolePolicy.JUDGE,
        prompt="judge candidate",
        response_schema="dummy",
        allow_fallback=True,
    )
    resp = engine.generate_structured(req, None)

    assert resp.ok is True
    assert resp.attempts == 2
    assert resp.data["title"] == "from_fallback"
    assert resp.provider == "gpt-5.6-luna"


def test_engine_all_retries_exhausted_fail_closed() -> None:
    events: list[PipelineEvent] = []

    def _invoke(_payload: dict[str, str]) -> Any:
        raise RuntimeError("Persistent network outage")

    engine = LangChainRoleEngine(
        chains={RolePolicy.CRITIC: RunnableLambda(_invoke)},
        max_transient_retries=2,
        on_event=events.append,
    )

    req = StructuredRequest(
        request_id="req-5",
        role=RolePolicy.CRITIC,
        prompt="criticize",
        response_schema="dummy",
    )
    resp = engine.generate_structured(req, None)

    assert resp.ok is False
    assert resp.error is not None
    assert resp.error.code == ProviderErrorCode.INFRA_ERROR
    assert resp.attempts == 3  # 1st try + 2 retries
    assert len(events) == 1
    assert events[0].type == "llm_call"
    assert events[0].data["ok"] is False

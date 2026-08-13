"""T08 — 일시적 공급자 오류(빈 응답) 재시도 테스트.

DeepSeek 가 response_format=json_object 요청에 간헐적으로 빈 content 를 반환할 때
(EMPTY_RESPONSE), 엔진이 원본 프롬프트로 재시도해야 한다. 스키마 오류와 달리
복구 프롬프트를 붙이면 오히려 응답을 망칠 수 있으므로 원본 그대로 재시도한다.
"""

from __future__ import annotations

from tests.contract.providers.test_structured_output import TangentAnalysis

from math_variant.providers.base import ModelPolicy, RawCompletion
from math_variant.providers.contracts import (
    ProviderErrorCode,
    RolePolicy,
    StructuredRequest,
)
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine


class FakeProvider:
    """순차 응답을 소비하는 테스트 공급자."""

    def __init__(self, name: str, responses: list[str]) -> None:
        self.name = name
        self.responses = list(responses)
        self.calls: list[str] = []

    def complete(self, prompt: str, policy: ModelPolicy) -> RawCompletion:
        self.calls.append(prompt)
        raw = self.responses.pop(0) if self.responses else ""
        return RawCompletion(
            raw_text=raw, latency_ms=10, cost_usd=0.0, provider=self.name, model=policy.model
        )


def _registry() -> SchemaRegistry:
    reg = SchemaRegistry()
    reg.register(TangentAnalysis)
    return reg


def _request() -> StructuredRequest:
    return StructuredRequest(
        request_id="r1",
        role=RolePolicy.SOURCE_ANALYZER,
        prompt="p",
        response_schema="TangentAnalysis",
    )


def _policy() -> ModelPolicy:
    return ModelPolicy(provider="fake", model="test-model")


def test_empty_response_retries_with_original_prompt() -> None:
    valid = __import__("json").dumps({"center": "(0,0)", "radius": "2", "line": "y=x", "goal": "x"})
    provider = FakeProvider("fake", ["", valid])  # 첫 시도 빈 응답, 재시도 성공

    engine = StructuredOutputEngine(
        primary=provider,
        fallback=None,
        schemas=_registry(),
        max_transient_retries=2,
    )
    response = engine.generate_structured(_request(), _policy())

    assert response.ok is True
    assert response.data is not None
    assert len(provider.calls) == 2  # 빈 응답 1회 + 재시도 1회
    # 재시도는 원본 프롬프트 그대로(복구 메시지 없음)
    assert provider.calls[1] == "p"


def test_empty_response_exhausts_to_emitted_failure() -> None:
    provider = FakeProvider("fake", ["", "", "", "", "", "", "", ""])  # 전부 빈 응답

    engine = StructuredOutputEngine(
        primary=provider,
        fallback=None,
        schemas=_registry(),
        max_transient_retries=7,
    )
    response = engine.generate_structured(_request(), _policy())

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == ProviderErrorCode.EMPTY_RESPONSE
    # 1회 + 최대 재시도 7회 = 8회 시도
    assert len(provider.calls) == 8
    assert response.attempts == 8


def test_transient_retries_disabled_matches_old_behavior() -> None:
    provider = FakeProvider("fake", [""])

    engine = StructuredOutputEngine(
        primary=provider,
        fallback=None,
        schemas=_registry(),
        max_transient_retries=0,
    )
    response = engine.generate_structured(_request(), _policy())

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == ProviderErrorCode.EMPTY_RESPONSE
    assert len(provider.calls) == 1


def test_truncated_json_is_retried_as_transient() -> None:
    valid = __import__("json").dumps(
        {"center": "(0,0)", "radius": "2", "line": "y=x", "goal": "x"}
    )
    provider = FakeProvider("fake", ["{broken", valid])  # 잘린 JSON 후 성공

    engine = StructuredOutputEngine(
        primary=provider,
        fallback=None,
        schemas=_registry(),
        max_transient_retries=2,
    )
    response = engine.generate_structured(_request(), _policy())

    assert response.ok is True
    assert len(provider.calls) == 2
    # 잘린 JSON 재시도는 원본 프롬프트 그대로
    assert provider.calls[1] == "p"

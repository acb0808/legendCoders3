"""T08 — 공급자 어댑터가 JSON 응답 지시를 항상 주입하는지 테스트.

DeepSeek API 는 response_format=json_object 사용 시 프롬프트(또는 시스템 메시지)에
"json" 단어가 반드시 있어야 한다. 어댑터는 어떤 프롬프트가 와도 이 제약을 만족하도록
시스템 메시지로 JSON 응답 지시를 주입해야 한다.
"""

from __future__ import annotations

import json

import httpx

from math_variant.providers.base import ModelPolicy
from math_variant.providers.openai_adapter import OpenAICompatibleProvider


class _RecordingTransport(httpx.BaseTransport):
    """요청 본문을 캡처하는 테스트용 전송 계층."""

    def __init__(self) -> None:
        self.request_body: dict | None = None

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.request_body = json.loads(request.content.decode("utf-8"))
        payload = {
            "choices": [
                {
                    "message": {"content": '{"answer": 2}'},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"total_tokens": 10},
        }
        return httpx.Response(200, json=payload, request=request)


def _provider(transport: _RecordingTransport) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name="deepseek",
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
        client=httpx.Client(transport=transport),
    )


def test_json_instruction_injected_as_system_message() -> None:
    transport = _RecordingTransport()
    provider = _provider(transport)

    provider.complete(
        "문제를 변형해라.",
        ModelPolicy(provider="deepseek", model="deepseek-v4-flash"),
    )

    assert transport.request_body is not None
    messages = transport.request_body["messages"]
    # 시스템 메시지가 항상 맨 앞에 주입되어 "json" 단어를 보장한다
    assert messages[0]["role"] == "system"
    assert "json" in messages[0]["content"].lower()
    # 원본 사용자 프롬프트는 그대로 유지된다
    assert messages[1] == {"role": "user", "content": "문제를 변형해라."}


def test_user_prompt_without_json_still_meets_requirement() -> None:
    transport = _RecordingTransport()
    provider = _provider(transport)

    provider.complete(
        "JSON이 전혀 없는 한글 프롬프트",
        ModelPolicy(provider="deepseek", model="deepseek-v4-flash"),
    )

    assert transport.request_body is not None
    messages = transport.request_body["messages"]
    joined = " ".join(m.get("content", "") for m in messages).lower()
    assert "json" in joined


def test_temperature_omitted_for_flaky_flash() -> None:
    """deepseek-v4-flash 는 temperature 를 보내면 빈 응답이 잦다.

    실측: temp=0.7 에서 2/4, temp 제거 시 0/4 빈 응답. 온도를 아예 보내지 않는다.
    """
    transport = _RecordingTransport()
    provider = _provider(transport)

    provider.complete(
        "문제를 생성해라.",
        ModelPolicy(provider="deepseek", model="deepseek-v4-flash"),
    )

    assert transport.request_body is not None
    assert "temperature" not in transport.request_body


def test_max_tokens_param_by_provider() -> None:
    """luna 는 max_completion_tokens, deepseek 는 max_tokens 를 사용한다."""
    from math_variant.providers.secondary_adapter import DeepSeekProvider

    # deepseek
    transport_ds = _RecordingTransport()
    ds = DeepSeekProvider(
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
        client=httpx.Client(transport=transport_ds),
    )
    ds.complete("문제", ModelPolicy(provider="deepseek", model="deepseek-v4-flash"))
    assert transport_ds.request_body is not None
    assert "max_tokens" in transport_ds.request_body
    assert "max_completion_tokens" not in transport_ds.request_body

    # luna (openai 계열)
    transport_luna = _RecordingTransport()
    luna = OpenAICompatibleProvider(
        name="openai",
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        client=httpx.Client(transport=transport_luna),
    )
    luna.complete("문제", ModelPolicy(provider="openai", model="gpt-5.6-luna"))
    assert transport_luna.request_body is not None
    assert "max_completion_tokens" in transport_luna.request_body
    assert "max_tokens" not in transport_luna.request_body

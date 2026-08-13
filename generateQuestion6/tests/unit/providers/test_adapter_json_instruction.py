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


class _StreamingTransport(httpx.BaseTransport):
    """SSE 스트리밍 응답을 반환하는 테스트용 전송 계층."""

    def __init__(self) -> None:
        self.request_body: dict | None = None

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.request_body = json.loads(request.content.decode("utf-8"))
        sse = (
            'data: {"choices":[{"delta":{"role":"assistant","reasoning_content":"Think"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"{\\"a\\": "}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"1}"}}]}\n\n'
            'data: {"usage":{"total_tokens": 5}}\n\n'
            "data: [DONE]\n\n"
        )
        return httpx.Response(
            200,
            content=sse.encode("utf-8"),
            request=request,
            headers={"Content-Type": "text/event-stream"},
        )


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


def test_output_length_limit_omitted() -> None:
    """출력 길이 제한(max_tokens/max_completion_tokens)을 요청에 담지 않는다.

    고정 상한은 긴 reasoning 이 먼저 출력될 때 최종 content 를 잘라 빈 응답을 만든다.
    공급자 기본 상한에 맡긴다. (사용자 요청)
    """
    for provider_name, transport in (
        ("deepseek", _RecordingTransport()),
        ("openai", _RecordingTransport()),
    ):
        provider = OpenAICompatibleProvider(
            name=provider_name,
            api_key="test-key",
            base_url="https://api.example.com/v1",
            client=httpx.Client(transport=transport),
        )
        provider.complete(
            "문제",
            ModelPolicy(provider=provider_name, model="m"),
        )
        assert transport.request_body is not None
        assert "max_tokens" not in transport.request_body
        assert "max_completion_tokens" not in transport.request_body


def test_streaming_sends_stream_and_delivers_deltas() -> None:
    """on_delta 가 주어지면 stream=true 로 요청하고 토큰 조각을 콜백으로 전달한다."""
    transport = _StreamingTransport()
    provider = OpenAICompatibleProvider(
        name="deepseek",
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
        client=httpx.Client(transport=transport),
    )

    deltas: list[tuple[str, str]] = []

    def on_delta(content_delta: str, reasoning_delta: str) -> None:
        deltas.append((content_delta, reasoning_delta))

    result = provider.complete(
        "문제를 생성해라.",
        ModelPolicy(provider="deepseek", model="deepseek-v4-flash"),
        on_delta=on_delta,
    )

    assert transport.request_body is not None
    assert transport.request_body["stream"] is True
    assert transport.request_body["stream_options"] == {"include_usage": True}
    # reasoning 조각과 content 조각이 순서대로 콜백에 전달된다
    assert ("", "Think") in deltas
    assert ('{"a": ', "") in deltas
    assert ("1}", "") in deltas
    # 최종 content 는 누적되어 반환된다
    assert result.raw_text == '{"a": 1}'
    # usage 청크에서 비용이 계산된다
    assert result.cost_usd == 5 / 1_000_000


def test_streaming_omits_temperature_like_non_streaming() -> None:
    """스트리밍 요청도 temperature 를 보내지 않는다."""
    transport = _StreamingTransport()
    provider = OpenAICompatibleProvider(
        name="deepseek",
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
        client=httpx.Client(transport=transport),
    )
    provider.complete(
        "문제",
        ModelPolicy(provider="deepseek", model="deepseek-v4-flash"),
        on_delta=lambda c, r: None,
    )
    assert transport.request_body is not None
    assert "temperature" not in transport.request_body

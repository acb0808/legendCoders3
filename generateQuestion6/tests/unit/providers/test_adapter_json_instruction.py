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
        ModelPolicy(provider="deepseek", model="deepseek-chat", temperature=0.2),
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
        ModelPolicy(provider="deepseek", model="deepseek-chat", temperature=0.3),
    )

    assert transport.request_body is not None
    messages = transport.request_body["messages"]
    joined = " ".join(m.get("content", "") for m in messages).lower()
    assert "json" in joined

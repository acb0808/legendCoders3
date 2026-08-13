"""OpenAI 호환 공급자 어댑터 (T02.3).

httpx 를 통해 chat/completions 를 호출하고, 구조화 출력(response_format json_object)을
요청한다. 비밀 키는 이 계층에서만 사용되고 로그에 남기지 않는다.

스트리밍(T09): on_delta 콜백이 주어지면 stream=true 로 요청해 토큰 조각을
(content, reasoning_content) 쌍으로 실시간 전달한다. deepseek-v4-flash 는
reasoning_content(추론 과정)를 먼저 내보낸 뒤 최종 content 를 스트리밍한다.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from math_variant.providers.base import ModelPolicy, RawCompletion, StreamDeltaCallback


class OpenAICompatibleProvider:
    """OpenAI-compatible 엔드포인트를 호출하는 공급자."""

    def __init__(
        self,
        name: str,
        api_key: str,
        base_url: str,
        client: httpx.Client | None = None,
        timeout_seconds: float = 600.0,
    ) -> None:
        self.name = name
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._client = client

    def _ensure_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self._timeout)
        return self._client

    def complete(
        self,
        prompt: str,
        policy: ModelPolicy,
        on_delta: StreamDeltaCallback | None = None,
    ) -> RawCompletion:
        client = self._ensure_client()
        # DeepSeek 는 response_format=json_object 사용 시 프롬프트에 "json" 단어가
        # 반드시 있어야 400 을 반환하지 않는다. 어떤 프롬프트가 와도 만족하도록
        # 시스템 메시지로 JSON 응답 지시를 항상 주입한다. (T08)
        body: dict[str, object] = {
            "model": policy.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You must respond in JSON format only.",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        # temperature 는 의도적으로 보내지 않는다:
        # - deepseek-v4-flash 는 temperature 를 보내면 빈 응답이 잦다 (실측 temp 제거 시 0/4)
        # - gpt-5.6-luna 는 temperature 를 지원하지 않는다 (기본값 1 만 허용)
        # 출력 길이 제한(max_tokens/max_completion_tokens)은 보내지 않는다:
        # - 고정 상한은 긴 reasoning 이 먼저 출력될 때 최종 content 를 잘라 빈 응답을 만든다.
        # - 공급자 기본 상한에 맡긴다. (사용자 요청)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if on_delta is None:
            response = client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            return RawCompletion(
                raw_text=content,
                provider=self.name,
                model=policy.model,
                cost_usd=float(payload.get("usage", {}).get("total_tokens", 0)) / 1_000_000,
            )

        # 스트리밍 경로: SSE 로 토큰 조각을 받으며 누적한다.
        body["stream"] = True
        body["stream_options"] = {"include_usage": True}
        content_parts: list[str] = []
        cost_usd = 0.0
        with client.stream(
            "POST",
            f"{self._base_url}/chat/completions",
            headers=headers,
            json=body,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    break
                chunk: dict[str, Any] = json.loads(data)
                usage = chunk.get("usage")
                if usage:
                    cost_usd = float(usage.get("total_tokens", 0)) / 1_000_000
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content_delta = delta.get("content") or ""
                reasoning_delta = delta.get("reasoning_content") or ""
                if content_delta:
                    content_parts.append(content_delta)
                if content_delta or reasoning_delta:
                    on_delta(content_delta, reasoning_delta)
        return RawCompletion(
            raw_text="".join(content_parts),
            provider=self.name,
            model=policy.model,
            cost_usd=cost_usd,
        )

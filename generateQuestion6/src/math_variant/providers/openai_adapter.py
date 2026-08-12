"""OpenAI 호환 공급자 어댑터 (T02.3).

httpx 를 통해 chat/completions 를 호출하고, 구조화 출력(response_format json_object)을
요청한다. 비밀 키는 이 계층에서만 사용되고 로그에 남기지 않는다.
"""

from __future__ import annotations

import httpx

from math_variant.providers.base import ModelPolicy, RawCompletion


class OpenAICompatibleProvider:
    """OpenAI-compatible 엔드포인트를 호출하는 공급자."""

    def __init__(
        self,
        name: str,
        api_key: str,
        base_url: str,
        client: httpx.Client | None = None,
        timeout_seconds: float = 120.0,
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

    def complete(self, prompt: str, policy: ModelPolicy) -> RawCompletion:
        client = self._ensure_client()
        body = {
            "model": policy.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": policy.temperature,
            "max_tokens": policy.max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
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

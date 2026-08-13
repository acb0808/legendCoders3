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
        # 공급자별 토큰 상한 파라미터명: luna(openai 계열)는 max_completion_tokens,
        # deepseek 는 max_tokens 를 쓴다.
        token_key = "max_tokens" if self.name == "deepseek" else "max_completion_tokens"
        body[token_key] = policy.max_tokens
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

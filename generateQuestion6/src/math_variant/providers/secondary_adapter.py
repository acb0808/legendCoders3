"""보조 공급자 어댑터 (DeepSeek) — 폴백 경로 (T02.3).

OpenAI 호환 계약을 재사용한다. 모델 정책은 역할 설정에서 결정된다.
"""

from __future__ import annotations

import httpx

from math_variant.providers.openai_adapter import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek API 공급자."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        client: httpx.Client | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        super().__init__(
            name="deepseek",
            api_key=api_key,
            base_url=base_url,
            client=client,
            timeout_seconds=timeout_seconds,
        )

"""공급자 레지스트리 팩토리 — 설정으로부터 실제 공급자를 구성한다."""

from __future__ import annotations

from math_variant.providers.base import LLMProvider
from math_variant.providers.openai_adapter import OpenAICompatibleProvider
from math_variant.providers.secondary_adapter import DeepSeekProvider
from math_variant.providers.settings import ProviderSettings


def build_provider_registry(settings: ProviderSettings) -> dict[str, LLMProvider]:
    """설정을 보고 공급자 인스턴스를 구성한다. 비밀은 공급자 내부에서만 사용된다."""
    registry: dict[str, LLMProvider] = {}
    if settings.openai_api_key:
        registry["openai"] = OpenAICompatibleProvider(
            name="openai",
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    if settings.deepseek_api_key:
        registry["deepseek"] = DeepSeekProvider(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return registry

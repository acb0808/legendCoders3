"""T02.3 — 실제 공급자 스모크 테스트 (MATH_VARIANT_LIVE_PROVIDER_TESTS=1 일 때만 실행)."""

from __future__ import annotations

import os

import pytest

from math_variant.providers.base import ModelPolicy
from math_variant.providers.factory import build_provider_registry
from math_variant.providers.settings import ProviderSettings

pytestmark = pytest.mark.live_provider


def test_openai_adapter_roundtrip() -> None:
    """설정의 키로 OpenAI-compatible 공급자를 구성해 원시 완성을 받는다."""
    settings = ProviderSettings()
    if not settings.openai_api_key:
        pytest.skip("OPENAI_API_KEY 가 설정되지 않음")
    registry = build_provider_registry(settings)
    provider = registry["openai"]
    completion = provider.complete(
        '1+1은? JSON으로 {"answer": 2} 반환.',
        ModelPolicy(provider="openai", model=os.environ.get("OPENAI_MODEL", "gpt-5-mini")),
    )
    assert '"answer"' in completion.raw_text


def test_deepseek_adapter_roundtrip() -> None:
    settings = ProviderSettings()
    if not settings.deepseek_api_key:
        pytest.skip("DEEPSEEK_API_KEY 가 설정되지 않음")
    registry = build_provider_registry(settings)
    provider = registry["deepseek"]
    completion = provider.complete(
        '1+1은? JSON으로 {"answer": 2} 반환.',
        ModelPolicy(provider="deepseek", model=settings.deepseek_model_flash),
    )
    assert '"answer"' in completion.raw_text

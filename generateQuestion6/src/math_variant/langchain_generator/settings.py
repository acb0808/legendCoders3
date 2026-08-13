"""LangChain 모듈의 LLM 설정 — 기존 ProviderSettings 를 재사용한다.

DeepSeek/OpenAI 호환 엔드포인트를 `ChatOpenAI(base_url=...)` 로 구성한다.
비밀 키는 ChatOpenAI 내부에서만 사용되고 로그에 남기지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from math_variant.providers.settings import ProviderSettings


@dataclass(frozen=True)
class LangChainLLMConfig:
    """ChatOpenAI 를 구성하기 위한 공급자·모델 스냅샷."""

    provider: str
    model: str
    api_key: str
    base_url: str


def resolve_llm_config(provider: str = "deepseek", model: str | None = None) -> LangChainLLMConfig:
    """.env 로부터 LangChain LLM 설정을 읽는다.

    텍스트 생성 역할(planner·ideator·generator)은 기본적으로 deepseek flash 모델을 쓰고,
    provider="openai" 인 경우 vision 전용 luna 모델로 해석한다.
    """
    settings = ProviderSettings()
    if provider == "openai":
        return LangChainLLMConfig(
            provider="openai",
            model=model or "gpt-5.6-luna",
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    return LangChainLLMConfig(
        provider="deepseek",
        model=model or settings.deepseek_model_flash,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )


def build_chat_model(config: LangChainLLMConfig) -> ChatOpenAI:
    """공급자 설정으로 ChatOpenAI 인스턴스를 만든다.

    기존 공급자 어댑터와 동일하게 temperature 를 보내지 않는다(temperature=None).
    deepseek-v4-flash 는 temperature 를 보내면 빈 응답이 잦고, gpt-5.6-luna 는
    temperature 를 지원하지 않는다.
    """
    return ChatOpenAI(
        model=config.model,
        api_key=SecretStr(config.api_key),
        base_url=config.base_url,
        temperature=None,
    )

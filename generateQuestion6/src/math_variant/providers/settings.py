"""공급자 설정 (pydantic-settings) — .env에서 키·모델·역할 정책을 읽는다."""

from __future__ import annotations

import json

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from math_variant.errors import ErrorCode, MathVariantError, StructuredError
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.resolver import RolePolicyConfig, RolePolicyEntry


def _default_roles(flash_model: str) -> dict[RolePolicy, RolePolicyEntry]:
    """역할 기본 정책을 반환한다. 텍스트 역할은 flash 모델, 비전 역할은 luna 모델.

    temperature 는 사용하지 않는다 — deepseek-v4-flash 는 temperature 를 보내면 빈 응답이
    잦고, gpt-5.6-luna 는 temperature 를 지원하지 않는다. 공급자 어댑터가 온도를 생략한다.
    """
    text_roles = {
        RolePolicy.SOURCE_ANALYZER,
        RolePolicy.GENERATOR,
        RolePolicy.BLIND_SOLVER,
        RolePolicy.CRITIC,
        RolePolicy.PLANNER,
        RolePolicy.IDEATOR,
        RolePolicy.SELECTOR,
        RolePolicy.CODE_REVIEWER,
        RolePolicy.JUDGE,
    }
    roles: dict[RolePolicy, RolePolicyEntry] = {
        role: RolePolicyEntry(provider="deepseek", model=flash_model) for role in text_roles
    }
    roles[RolePolicy.VISION] = RolePolicyEntry(provider="openai", model="gpt-5.6-luna")
    return roles


class ProviderSettings(BaseSettings):
    """공급자별 비밀·엔드포인트·모델·역할 정책."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://api.openai.com/v1")

    deepseek_api_key: str = Field(default="")
    deepseek_base_url: str = Field(default="https://api.deepseek.com/v1")
    deepseek_model_flash: str = Field(default="deepseek-v4-flash")

    # 역할 정책 재정의: JSON {"source_analyzer": {"provider": "...", "model": "..."}}
    role_policy_json: str = Field(default="")

    def role_policy(self) -> RolePolicyConfig:
        """역할 정책을 반환한다. JSON 재정의는 기본값 위에 얹는다."""
        if not self.role_policy_json.strip():
            return RolePolicyConfig(roles=_default_roles(self.deepseek_model_flash))
        roles = _default_roles(self.deepseek_model_flash)
        try:
            raw: dict[str, object] = json.loads(self.role_policy_json)
            for role_str, entry in raw.items():
                role = RolePolicy(role_str)
                roles[role] = RolePolicyEntry.model_validate(entry)
        except (json.JSONDecodeError, ValueError, AttributeError, ValidationError) as exc:
            raise MathVariantError(
                StructuredError(
                    code=ErrorCode.PARSE_REJECTED,
                    message="역할 정책 설정이 잘못되었다",
                    context={"role_policy_json": self.role_policy_json},
                )
            ) from exc
        return RolePolicyConfig(roles=roles)

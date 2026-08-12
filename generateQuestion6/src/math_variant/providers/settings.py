"""공급자 설정 (pydantic-settings) — .env에서 키·모델·역할 정책을 읽는다."""

from __future__ import annotations

import json

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from math_variant.providers.contracts import RolePolicy
from math_variant.providers.resolver import RolePolicyConfig, RolePolicyEntry


def _default_roles(flash_model: str) -> dict[RolePolicy, RolePolicyEntry]:
    """역할 기본 정책을 반환한다. 텍스트 역할은 flash 모델, 비전 역할은 luna 모델."""
    text_roles = {
        RolePolicy.SOURCE_ANALYZER: 0.2,
        RolePolicy.GENERATOR: 0.7,
        RolePolicy.BLIND_SOLVER: 0.2,
        RolePolicy.CRITIC: 0.2,
        RolePolicy.PLANNER: 0.2,
        RolePolicy.IDEATOR: 1.4,
        RolePolicy.SELECTOR: 0.3,
        RolePolicy.CODE_REVIEWER: 0.2,
        RolePolicy.JUDGE: 0.2,
    }
    roles: dict[RolePolicy, RolePolicyEntry] = {
        role: RolePolicyEntry(provider="deepseek", model=flash_model, temperature=temperature)
        for role, temperature in text_roles.items()
    }
    roles[RolePolicy.VISION] = RolePolicyEntry(
        provider="openai", model="gpt-5.6-luna", temperature=0.4
    )
    return roles


class ProviderSettings(BaseSettings):
    """공급자별 비밀·엔드포인트·모델·역할 정책."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://api.openai.com/v1")

    deepseek_api_key: str = Field(default="")
    deepseek_base_url: str = Field(default="https://api.deepseek.com/v1")
    deepseek_model_flash: str = Field(default="deepseek-chat")
    deepseek_model_pro: str = Field(default="deepseek-reasoner")

    # 역할 정책 재정의: JSON {"source_analyzer": {"provider": "...", "model": "..."}}
    role_policy_json: str = Field(default="")

    def role_policy(self) -> RolePolicyConfig:
        """역할 정책을 반환한다. 미설정 시 기본값 사용."""
        if not self.role_policy_json.strip():
            return RolePolicyConfig(roles=_default_roles(self.deepseek_model_flash))
        raw = json.loads(self.role_policy_json)
        roles: dict[RolePolicy, RolePolicyEntry] = {}
        for role_str, entry in raw.items():
            role = RolePolicy(role_str)
            roles[role] = RolePolicyEntry.model_validate(entry)
        return RolePolicyConfig(roles=roles)

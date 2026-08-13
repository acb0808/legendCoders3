"""역할 정책 리졸버 — 설정만으로 provider·model 을 바꾼다 (T02.3-CT5).

비즈니스 코드는 `RolePolicy` 만 참조하고, 실제 provider·model·폴백은
설정(RolePolicyConfig) + 공급자 레지스트리로 결정된다.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from math_variant.errors import ErrorCode, MathVariantError, StructuredError
from math_variant.providers.base import LLMProvider, ModelPolicy
from math_variant.providers.contracts import RolePolicy


class RolePolicyEntry(BaseModel):
    """역할 하나에 대한 공급자·모델 스냅샷."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    model: str
    max_tokens: int = Field(default=4096, ge=1)
    fallback_provider: str | None = None
    fallback_model: str | None = None


class RolePolicyConfig(BaseModel):
    """역할 → 공급자·모델 매핑 (설정 전용 객체)."""

    model_config = ConfigDict(extra="forbid")

    roles: dict[RolePolicy, RolePolicyEntry]


class RoleResolver:
    """역할을 provider·ModelPolicy 로 해석한다."""

    def __init__(self, config: RolePolicyConfig, registry: dict[str, LLMProvider]) -> None:
        self._config = config
        self._registry = registry

    def entry(self, role: RolePolicy) -> RolePolicyEntry:
        try:
            return self._config.roles[role]
        except KeyError as exc:
            raise MathVariantError(
                StructuredError(
                    code=ErrorCode.UNSUPPORTED_CONCEPT,
                    message=f"역할 정책이 설정되지 않았다: {role.value}",
                    context={"role": role.value},
                )
            ) from exc

    def policy_for(self, role: RolePolicy) -> ModelPolicy:
        entry = self.entry(role)
        return ModelPolicy(
            provider=entry.provider,
            model=entry.model,
            max_tokens=entry.max_tokens,
        )

    def provider_for(self, role: RolePolicy) -> LLMProvider:
        entry = self.entry(role)
        try:
            return self._registry[entry.provider]
        except KeyError as exc:
            raise MathVariantError(
                StructuredError(
                    code=ErrorCode.UNSUPPORTED_CONCEPT,
                    message=f"공급자 레지스트리에 없는 공급자: {entry.provider}",
                    context={"provider": entry.provider, "role": role.value},
                )
            ) from exc

    def fallback_for(self, role: RolePolicy) -> LLMProvider | None:
        entry = self.entry(role)
        if entry.fallback_provider is None:
            return None
        try:
            return self._registry[entry.fallback_provider]
        except KeyError as exc:
            raise MathVariantError(
                StructuredError(
                    code=ErrorCode.UNSUPPORTED_CONCEPT,
                    message=f"폴백 공급자가 레지스트리에 없다: {entry.fallback_provider}",
                    context={"provider": entry.fallback_provider},
                )
            ) from exc

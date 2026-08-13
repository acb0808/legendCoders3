"""공급자 인터페이스와 역할 정책 (T02.3).

원칙: 비즈니스 코드는 공급자·모델명 대신 `RolePolicy` 를 사용하고,
실제 provider·model 은 설정(RolePolicyConfig)이 결정한다. 모델 교체가 코드 수정을
요구하지 않는다. (T02.3-CT5)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from math_variant.providers.contracts import RolePolicy

# 토큰 델타 콜백: (content_delta, reasoning_delta). 둘 다 비어 있을 수 있다.
StreamDeltaCallback = Callable[[str, str], None]


class ModelPolicy(BaseModel):
    """공급자 이름과 모델 스냅샷."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    model: str
    max_tokens: int = Field(default=4096, ge=1)


class RawCompletion(BaseModel):
    """공급자가 반환한 원시 완성 (구조화 검증 전)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_text: str
    latency_ms: int = 0
    cost_usd: float = 0.0
    provider: str
    model: str


@runtime_checkable
class LLMProvider(Protocol):
    """교체 가능한 공급자 경계.

    신뢰하지 않는 코드가 아니라 결정론적 구조화 계층이 파싱·검증을 담당한다.
    """

    name: str

    def complete(
        self,
        prompt: str,
        policy: ModelPolicy,
        on_delta: StreamDeltaCallback | None = None,
    ) -> RawCompletion: ...


RolePrompt = str


class RolePromptBundle(BaseModel):
    """역할별 프롬프트 묶음 (원문 전문 노출 방지를 위해 본문을 분리 저장)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: RolePolicy
    system: str = Field(min_length=1)
    task: str = Field(min_length=1)

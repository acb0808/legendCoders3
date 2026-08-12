"""구조화 출력 계약 (T02.3)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RolePolicy(StrEnum):
    """모델명 대신 비즈니스 코드가 참조하는 역할 정책."""

    SOURCE_ANALYZER = "source_analyzer"
    GENERATOR = "generator"
    BLIND_SOLVER = "blind_solver"
    CRITIC = "critic"
    PLANNER = "planner"
    IDEATOR = "ideator"
    SELECTOR = "selector"
    CODE_REVIEWER = "code_reviewer"
    JUDGE = "judge"
    VISION = "vision"


class ProviderErrorCode(StrEnum):
    """구조화된 출력 오류 코드."""

    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    TRUNCATED_JSON = "TRUNCATED_JSON"
    SCHEMA_VALIDATION = "SCHEMA_VALIDATION"
    REPAIR_FAILED = "REPAIR_FAILED"
    ALL_PROVIDERS_FAILED = "ALL_PROVIDERS_FAILED"
    INFRA_ERROR = "INFRA_ERROR"
    INVALID_SCHEMA = "INVALID_SCHEMA"


class ProviderError(BaseModel):
    """잘못된 출력이 다음 단계로 전달되는 것을 막는 구조화된 오류."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: ProviderErrorCode
    message: str
    detail: str = Field(default="")
    provider: str | None = None
    attempt: int = 0


class StructuredRequest(BaseModel):
    """구조화 생성 요청.

    `api_key_guard`는 테스트에서 로그 비밀 차단을 검증하기 위한 용도이며,
    실제 샌드박스·공급자 요청 계약에는 비밀 타입이 참조될 수 없다. (T03.1-CT2)
    """

    model_config = ConfigDict(extra="forbid")

    request_id: str
    role: RolePolicy
    prompt: str
    response_schema: str
    max_repair_attempts: int = Field(default=1, ge=0, le=1)
    allow_fallback: bool = True
    api_key_guard: str | None = None


class ProviderResponse(BaseModel):
    """구조화 생성 결과 (성공 또는 구조화된 오류)."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    ok: bool
    data: dict[str, Any] | None = None
    error: ProviderError | None = None
    provider: str | None = None
    model_policy: str | None = None
    attempts: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0

    @property
    def status(self) -> Literal["ok", "error"]:
        return "ok" if self.ok else "error"

"""샌드박스 실행 계약 (T03.1).

보안 경계:
- 요청 계약은 비밀 타입(api_key, db_url 등)을 참조할 수 없다.
- input_json·code 에 비밀/호스트 경로 패턴이 있으면 정책 위반으로 거부한다.
- 상태를 COMPLETED, CODE_ERROR, TIMEOUT, POLICY_VIOLATION, INFRA_ERROR 로 구분한다.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

BLOCKED_FIELD_PATTERNS = (
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"^db_?url$", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"secret[_a-z]*", re.IGNORECASE),
    re.compile(r"^token$", re.IGNORECASE),
    re.compile(r"host[_ ]?path", re.IGNORECASE),
    re.compile(r"^home$", re.IGNORECASE),
    re.compile(r"^ssh", re.IGNORECASE),
)

HOST_PATH_PATTERNS = (
    re.compile(r"/etc/passwd"),
    re.compile(r"/etc/shadow"),
    re.compile(r"\.ssh"),
    re.compile(r"[A-Za-z]:\\\\Users"),
    re.compile(r"os\.environ"),
)


class SandboxStatus(StrEnum):
    COMPLETED = "COMPLETED"
    CODE_ERROR = "CODE_ERROR"
    TIMEOUT = "TIMEOUT"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    INFRA_ERROR = "INFRA_ERROR"


class ResourceBudget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cpu_seconds: int = Field(default=10, ge=1, le=300)
    memory_mb: int = Field(default=256, ge=16, le=4096)
    max_output_chars: int = Field(default=20000, ge=100)


class SandboxRequest(BaseModel):
    """신뢰하지 않는 코드 실행 요청.

    코드, 입력 JSON, 허용 패키지 세트, 자원 예산, 시드, 기대 출력 스키마를 포함한다.
    애플리케이션 비밀 설정 타입은 이 계약에서 참조될 수 없다. (CT2)
    """

    model_config = ConfigDict(extra="forbid")

    request_id: str
    code: str = Field(min_length=1)
    input_json: dict[str, Any] = Field(default_factory=dict)
    allowed_packages: list[str] = Field(default_factory=list)
    resource_budget: ResourceBudget = Field(default_factory=ResourceBudget)
    seed: int | None = None
    expected_output_schema: str | None = None

    @model_validator(mode="after")
    def _reject_secrets_and_host_paths(self) -> SandboxRequest:
        for key in self.input_json:
            if any(pattern.search(key) for pattern in BLOCKED_FIELD_PATTERNS):
                raise ValueError(f"입력 필드에 금지된 비밀/호스트 키가 있다: {key!r}")
        scan = self.code
        for pattern in HOST_PATH_PATTERNS:
            if pattern.search(scan):
                raise ValueError(f"코드에 금지된 호스트/비밀 접근 패턴이 있다: {pattern.pattern}")
        for pattern in BLOCKED_FIELD_PATTERNS:
            if pattern.search(scan):
                raise ValueError(f"코드에 금지된 비밀 키 문자열 패턴이 있다: {pattern.pattern}")
        return self


class SandboxResult(BaseModel):
    """샌드박스 실행 결과."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    result_id: str
    request_id: str
    status: SandboxStatus
    output_json: dict[str, Any] | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    image_digest: str | None = None
    package_versions: dict[str, str] = Field(default_factory=dict)
    provider_name: str = ""

    @property
    def completed(self) -> bool:
        return self.status == SandboxStatus.COMPLETED

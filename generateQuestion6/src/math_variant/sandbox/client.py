"""샌드박스 클라이언트 — 공급자와 오케스트레이터 사이의 계약 경계 (T03.1).

책임:
- 예외(타임아웃·인프라 오류)를 상태로 매핑한다. (CT3)
- 잘못된 결과 스키마를 ValidationEvidence 로 승격시키지 않는다. (CT4)
- 공급자 교체가 오케스트레이터 코드를 바꾸지 않게 한다. (CT5)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from math_variant.domain.validation import CheckResult
from math_variant.sandbox.contracts import (
    SandboxRequest,
    SandboxResult,
)
from math_variant.sandbox.provider import SandboxProvider


class SandboxExecutionStatus(StrEnum):
    COMPLETED = "COMPLETED"
    CODE_ERROR = "CODE_ERROR"
    TIMEOUT = "TIMEOUT"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    INFRA_ERROR = "INFRA_ERROR"


class SandboxExecution(BaseModel):
    """클라이언트가 반환하는 실행 기록."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str
    status: SandboxExecutionStatus
    result: SandboxResult | None = None
    evidence: CheckResult | None = None
    error_detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == SandboxExecutionStatus.COMPLETED


class SandboxClient:
    """샌드박스 실행 경계를 고정한 클라이언트."""

    def __init__(self, provider: SandboxProvider) -> None:
        self.provider = provider

    def run(self, request: SandboxRequest) -> SandboxExecution:
        try:
            result = self.provider.execute(request)
        except TimeoutError as exc:
            return SandboxExecution(
                request_id=request.request_id,
                status=SandboxExecutionStatus.TIMEOUT,
                error_detail=str(exc),
            )
        except Exception as exc:
            return SandboxExecution(
                request_id=request.request_id,
                status=SandboxExecutionStatus.INFRA_ERROR,
                error_detail=str(exc)[:300],
            )

        # 잘못된 결과 스키마는 검증되지 않은 상태로 승격시키지 않는다.
        if not self._is_valid_result(request, result):
            return SandboxExecution(
                request_id=request.request_id,
                status=SandboxExecutionStatus.INFRA_ERROR,
                error_detail="공급자가 유효하지 않은 결과 스키마를 반환했다",
            )

        execution_status = SandboxExecutionStatus(result.status.value)
        evidence = None
        if execution_status == SandboxExecutionStatus.COMPLETED:
            evidence = CheckResult(
                check_id=f"sandbox-{request.request_id}",
                kind="sandbox",
                status="PASS",
                critical=True,
                evidence={
                    "output": result.output_json,
                    "duration_ms": result.duration_ms,
                    "provider": result.provider_name or self.provider.name,
                    "image_digest": result.image_digest,
                    "package_versions": result.package_versions,
                },
            )
        return SandboxExecution(
            request_id=request.request_id,
            status=execution_status,
            result=result,
            evidence=evidence,
        )

    @staticmethod
    def _is_valid_result(request: SandboxRequest, result: Any) -> bool:
        if not isinstance(result, SandboxResult):
            return False
        if result.request_id != request.request_id:
            return False
        try:
            SandboxResult.model_validate(result.model_dump())
        except ValidationError:
            return False
        return True

"""검증 테스트 스크립트 러너 (T07).

생성기가 작성한 sympy 검증 스크립트를 샌드박스 공급자에서 실행하고
결정론적으로 PASS/FAIL/UNRESOLVED 를 판정한다.

스크립트 계약 (prompts/candidate_generator.md 참고):
- 전체 Python 스크립트로 sympy·math 등을 import 할 수 있다.
- 마지막에 `result = {"verdict": "PASS", "detail": "..."}` 를 설정해야 한다.
- 실패는 예외를 던지거나 result["verdict"] 를 "FAIL" 로 설정해 표현한다.
- 실행기(infra/sandbox/runner.py)는 `exec(code, sandbox_globals, data)` 로 실행하고
  스크립트가 설정한 `result` 를 output_json["result"] 로 반환한다.

판정은 스크립트 결과를 신뢰하지 않는다:
- COMPLETED + result.verdict == "PASS" 만 PASS.
- 그 외(실패/시간초과/거짓 결과/정책 위반/인프라 오류)는 FAIL 또는 UNRESOLVED.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from math_variant.sandbox.contracts import (
    ResourceBudget,
    SandboxRequest,
    SandboxResult,
    SandboxStatus,
)
from math_variant.sandbox.provider import SandboxProvider


class TestVerdict(StrEnum):
    __test__ = False  # pytest 컬렉션 경고 방지

    PASS = "PASS"  # noqa: S105 - 판정 상태 코드 (비밀 아님)
    FAIL = "FAIL"
    UNRESOLVED = "UNRESOLVED"


class VerificationOutcome(BaseModel):
    """검증 스크립트 실행 판정 결과."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    verdict: TestVerdict
    status: SandboxStatus
    detail: str = ""
    duration_ms: int = 0
    image_digest: str | None = None

    @property
    def passes(self) -> bool:
        return self.verdict == TestVerdict.PASS


def build_verification_request(
    request_id: str,
    verification_script: str,
    problem_context: dict[str, Any],
) -> SandboxRequest:
    """검증 스크립트를 샌드박스 요청으로 감싼다."""
    return SandboxRequest(
        request_id=request_id,
        code=verification_script,
        input_json=problem_context,
        allowed_packages=["sympy", "mpmath", "math", "fractions", "itertools", "collections"],
        resource_budget=ResourceBudget(cpu_seconds=20, max_output_chars=20000),
        expected_output_schema="verification_verdict",
    )


def run_verification(provider: SandboxProvider, request: SandboxRequest) -> VerificationOutcome:
    """샌드박스 공급자에서 검증 스크립트를 실행하고 판정한다."""
    return interpret(provider.execute(request))


def interpret(result: SandboxResult) -> VerificationOutcome:
    """샌드박스 실행 결과를 결정론적으로 판정한다."""
    if result.status == SandboxStatus.POLICY_VIOLATION:
        return VerificationOutcome(
            verdict=TestVerdict.UNRESOLVED,
            status=result.status,
            detail=result.stderr[:500],
            duration_ms=result.duration_ms,
        )
    if result.status == SandboxStatus.INFRA_ERROR:
        return VerificationOutcome(
            verdict=TestVerdict.UNRESOLVED,
            status=result.status,
            detail=result.stderr[:500],
            duration_ms=result.duration_ms,
        )
    if result.status == SandboxStatus.TIMEOUT:
        return VerificationOutcome(
            verdict=TestVerdict.FAIL,
            status=result.status,
            detail="검증 스크립트 실행 시간 초과",
            duration_ms=result.duration_ms,
        )
    if result.status == SandboxStatus.CODE_ERROR:
        return VerificationOutcome(
            verdict=TestVerdict.FAIL,
            status=result.status,
            detail=result.stderr[:500],
            duration_ms=result.duration_ms,
        )
    payload = result.output_json or {}
    inner = payload.get("result")
    if isinstance(inner, dict) and inner.get("verdict") == "PASS":
        return VerificationOutcome(
            verdict=TestVerdict.PASS,
            status=result.status,
            detail=str(inner.get("detail", ""))[:500],
            duration_ms=result.duration_ms,
            image_digest=result.image_digest,
        )
    return VerificationOutcome(
        verdict=TestVerdict.FAIL,
        status=result.status,
        detail=f"검증 스크립트가 PASS 를 반환하지 않았다: {inner!r}"[:500],
        duration_ms=result.duration_ms,
    )

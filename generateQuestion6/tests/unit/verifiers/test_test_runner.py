"""T07 — 검증 테스트 스크립트 러너 판정 테스트."""

from __future__ import annotations

import pytest
from pydantic_core import ValidationError

from math_variant.sandbox.contracts import SandboxResult, SandboxStatus
from math_variant.verifiers.test_runner import (
    TestVerdict,
    VerificationOutcome,
    build_verification_request,
    interpret,
)


def _result(status: SandboxStatus, output: dict | None = None, stderr: str = "") -> SandboxResult:
    return SandboxResult(
        result_id="r",
        request_id="req",
        status=status,
        output_json=output,
        stderr=stderr,
        duration_ms=10,
        image_digest="sha256:abc",
    )


def test_completed_with_pass_verdict_is_pass() -> None:
    outcome = interpret(_result(SandboxStatus.COMPLETED, {"result": {"verdict": "PASS"}}))
    assert outcome.verdict == TestVerdict.PASS


def test_completed_without_pass_verdict_is_fail() -> None:
    outcome = interpret(_result(SandboxStatus.COMPLETED, {"result": {"verdict": "FAIL"}}))
    assert outcome.verdict == TestVerdict.FAIL
    outcome2 = interpret(_result(SandboxStatus.COMPLETED, {"result": 42}))
    assert outcome2.verdict == TestVerdict.FAIL


def test_code_error_and_timeout_are_fail() -> None:
    assert (
        interpret(_result(SandboxStatus.CODE_ERROR, stderr="ZeroDivisionError")).verdict
        == TestVerdict.FAIL
    )
    assert interpret(_result(SandboxStatus.TIMEOUT)).verdict == TestVerdict.FAIL


def test_policy_and_infra_are_unresolved() -> None:
    assert (
        interpret(_result(SandboxStatus.POLICY_VIOLATION, stderr="금지 패턴")).verdict
        == TestVerdict.UNRESOLVED
    )
    assert interpret(_result(SandboxStatus.INFRA_ERROR)).verdict == TestVerdict.UNRESOLVED


def test_build_request_embeds_script_and_context() -> None:
    request = build_verification_request(
        "req-1",
        "from sympy import symbols\nresult = {'verdict': 'PASS'}",
        {"problem": "x=1"},
    )
    assert request.code.startswith("from sympy")
    assert request.input_json == {"problem": "x=1"}
    assert "sympy" in request.allowed_packages
    assert request.resource_budget.cpu_seconds == 20


def test_outcome_is_frozen() -> None:
    outcome = VerificationOutcome(verdict=TestVerdict.PASS, status=SandboxStatus.COMPLETED)
    with pytest.raises(ValidationError):
        outcome.verdict = TestVerdict.FAIL  # type: ignore[misc]


class _FakeProvider:
    name = "fake"

    def execute(self, request):
        return _result(SandboxStatus.COMPLETED, {"result": {"verdict": "PASS"}})


def test_run_verification_delegates_and_returns_pass() -> None:
    from math_variant.verifiers.test_runner import run_verification

    request = build_verification_request("req-x", "result = {'verdict': 'PASS'}", {})
    outcome = run_verification(_FakeProvider(), request)  # type: ignore[arg-type]
    assert outcome.verdict == TestVerdict.PASS

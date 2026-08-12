"""T07 — 실제 Docker 샌드박스에서 검증 스크립트 실행 통합 테스트."""

from __future__ import annotations

import pytest

from math_variant.sandbox.provider import DockerSandboxProvider
from math_variant.verifiers.test_runner import (
    TestVerdict,
    build_verification_request,
    run_verification,
)

pytestmark = pytest.mark.docker

_IMAGE = "math-variant-sandbox:test"


@pytest.fixture(scope="module")
def sandbox() -> DockerSandboxProvider:
    return DockerSandboxProvider(image=_IMAGE)


def test_sympy_script_passing_verdict(sandbox: DockerSandboxProvider) -> None:
    script = (
        "from sympy import symbols, sqrt\n"
        "x, a = symbols('x a')\n"
        "claimed = 8*sqrt(2)\n"
        "assert claimed == 8*sqrt(2)\n"
        "result = {'verdict': 'PASS', 'detail': 'claimed value matches'}\n"
    )
    request = build_verification_request("it-pass", script, {"problem_text": "문제"})
    outcome = run_verification(sandbox, request)
    assert outcome.verdict == TestVerdict.PASS
    assert outcome.image_digest is not None


def test_failing_script_is_fail(sandbox: DockerSandboxProvider) -> None:
    script = (
        "from sympy import symbols\n"
        "x = symbols('x')\n"
        "assert x**2 + 1 == 0, '실패해야 한다'\n"
        "result = {'verdict': 'PASS'}\n"
    )
    request = build_verification_request("it-fail", script, {})
    outcome = run_verification(sandbox, request)
    assert outcome.verdict == TestVerdict.FAIL
    assert outcome.status == "CODE_ERROR"


def test_blocked_script_rejected_at_request_build() -> None:
    script = "import os\nos.environ['X'] = '1'\nresult = {'verdict': 'PASS'}\n"
    with pytest.raises(ValueError):
        build_verification_request("it-blocked", script, {})


def test_restricted_import_script_is_fail(sandbox: DockerSandboxProvider) -> None:
    script = "import numpy\nresult = {'verdict': 'PASS'}\n"
    request = build_verification_request("it-mal", script, {})
    outcome = run_verification(sandbox, request)
    assert outcome.verdict == TestVerdict.FAIL
    assert outcome.status == "CODE_ERROR"

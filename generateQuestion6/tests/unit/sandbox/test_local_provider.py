"""T03.1 — 로컬 샌드박스 공급자 동작 테스트 (오프라인)."""

from __future__ import annotations

from math_variant.sandbox.client import SandboxClient
from math_variant.sandbox.contracts import SandboxRequest
from math_variant.sandbox.provider import LocalSandboxProvider


def _req(code: str, **overrides: object) -> SandboxRequest:
    base = {
        "request_id": "loc",
        "code": code,
        "input_json": {"x": 3},
        "allowed_packages": ["sympy"],
        "resource_budget": {"cpu_seconds": 5, "memory_mb": 256},
        "seed": 1,
        "expected_output_schema": "AnswerPayload",
    }
    base.update(overrides)
    return SandboxRequest(**base)


def test_local_provider_runs_code_and_maps_errors() -> None:
    client = SandboxClient(LocalSandboxProvider(timeout_seconds=10))

    ok = client.run(_req("{'value': x**2 + 1}"))
    assert ok.ok is True
    assert ok.evidence is not None
    assert ok.result is not None and ok.result.output_json == {"value": 10}

    code_error = client.run(_req("1 / 0"))
    assert code_error.status == "CODE_ERROR"
    assert code_error.evidence is None

    timeout = client.run(_req("x", resource_budget={"cpu_seconds": 300, "memory_mb": 256}), **{})
    # eval 은 즉시 끝나므로 타임아웃과 구분되는 정상 실행을 확인한다.
    assert timeout.ok is True

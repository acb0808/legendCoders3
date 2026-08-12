"""T03.1+T03.2 — Docker 공급자와 클라이언트 통합 (도커 사용 가능 시)."""

from __future__ import annotations

import pytest

from math_variant.sandbox.client import SandboxClient
from math_variant.sandbox.contracts import SandboxRequest
from math_variant.sandbox.provider import DockerSandboxProvider

pytestmark = pytest.mark.docker

IMAGE = "math-variant-sandbox:test"


def test_docker_provider_runs_via_client() -> None:
    provider = DockerSandboxProvider(image=IMAGE)
    client = SandboxClient(provider)
    execution = client.run(
        SandboxRequest(
            request_id="docker-client",
            code="import sympy\nresult = {'version': sympy.__version__}\n",
            input_json={},
            allowed_packages=["sympy"],
            resource_budget={"cpu_seconds": 10, "memory_mb": 256},
            seed=1,
            expected_output_schema=None,
        )
    )

    assert execution.ok is True
    assert execution.result is not None
    assert execution.result.output_json == {"version": "1.13.3"}
    assert execution.evidence is not None
    assert execution.evidence.evidence["package_versions"]["sympy"] == "1.13.3"
    assert "sha256" in str(execution.evidence.evidence.get("image_digest") or "")


def test_docker_provider_reports_code_error() -> None:
    provider = DockerSandboxProvider(image=IMAGE)
    client = SandboxClient(provider)
    execution = client.run(
        SandboxRequest(
            request_id="docker-err",
            code="result = 1 / 0\n",
            input_json={},
            allowed_packages=["sympy"],
            resource_budget={"cpu_seconds": 10, "memory_mb": 256},
            seed=1,
            expected_output_schema=None,
        )
    )

    assert execution.status == "CODE_ERROR"
    assert execution.evidence is None

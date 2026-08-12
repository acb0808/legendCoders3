"""T03.1 — 샌드박스 실행 계약과 교체 가능한 공급자 테스트.

- T03.1-CT1: 유효 요청과 결과가 JSON 직렬화 왕복 후 동일하다.
- T03.1-CT2: API 키·DB URL·호스트 경로 필드를 요청에 넣을 수 없다.
- T03.1-CT3: 시간 초과와 인프라 오류가 서로 다른 상태로 매핑된다.
- T03.1-CT4: 잘못된 결과 스키마는 ValidationEvidence로 승격되지 않는다.
- T03.1-CT5: provider 교체가 오케스트레이터 코드를 바꾸지 않는다.
"""

from __future__ import annotations

from pydantic import ValidationError

from math_variant.sandbox.client import SandboxClient, SandboxExecutionStatus
from math_variant.sandbox.contracts import (
    SandboxRequest,
    SandboxResult,
    SandboxStatus,
)


def _request(**overrides: object) -> SandboxRequest:
    base: dict = {
        "request_id": "r1",
        "code": "from math import sqrt\ndef solve():\n    return {'roots': [sqrt(4)]}\n",
        "input_json": {"a": 2},
        "allowed_packages": ["sympy", "math"],
        "resource_budget": {"cpu_seconds": 5, "memory_mb": 256},
        "seed": 42,
        "expected_output_schema": "AnswerPayload",
    }
    base.update(overrides)
    return SandboxRequest(**base)


def _result(**overrides: object) -> SandboxResult:
    base: dict = {
        "result_id": "res-1",
        "request_id": "r1",
        "status": "COMPLETED",
        "output_json": {"roots": [2]},
        "stdout": "",
        "stderr": "",
        "duration_ms": 12,
        "image_digest": "sha256:abc",
        "package_versions": {"sympy": "1.13.3"},
    }
    base.update(overrides)
    return SandboxResult(**base)


def test_ct1_json_roundtrip_is_identical() -> None:
    request = _request()
    result = _result()

    request_rt = SandboxRequest.model_validate_json(request.model_dump_json())
    result_rt = SandboxResult.model_validate_json(result.model_dump_json())

    assert request_rt == request
    assert result_rt == result
    assert result_rt.status == SandboxStatus.COMPLETED


def test_ct2_secret_and_host_fields_cannot_be_put_in_request() -> None:
    # 요청 스키마에 비밀 타입 필드가 아예 없고, 추가 필드는 extra=forbid 로 거부된다.
    try:
        SandboxRequest(
            request_id="r2",
            code="print(1)",
            input_json={},
            allowed_packages=["sympy"],
            resource_budget={},
            seed=1,
            expected_output_schema="AnswerPayload",
            api_key="sk-secret",  # type: ignore[call-arg]
        )
    except ValidationError:
        pass
    else:  # pragma: no cover
        raise AssertionError("요청에 API 키 필드를 넣을 수 있다")

    # input_json 에 비밀·호스트 키를 넣는 것도 차단된다.
    for bad_key in ["api_key", "db_url", "password", "host_path", "secret_token"]:
        try:
            _request(input_json={bad_key: "값"})
        except ValidationError:
            continue
        else:  # pragma: no cover
            raise AssertionError(f"input_json 에 비밀 필드({bad_key})를 넣을 수 있다")

    # 코드에 호스트 경로/비밀 패턴이 있으면 차단된다.
    for bad_code in [
        'print(open("/etc/passwd").read())',
        "import os; print(os.environ)",
        'secret = "sk-ABC"',
    ]:
        try:
            _request(code=bad_code)
        except ValidationError:
            continue
        else:  # pragma: no cover
            raise AssertionError(f"코드에 위험 패턴을 넣을 수 있다: {bad_code}")


class TimeoutProvider:
    name = "timeout"

    def execute(self, request: SandboxRequest) -> SandboxResult:
        raise TimeoutError("샌드박스 시간 초과")


class InfraProvider:
    name = "infra"

    def execute(self, request: SandboxRequest) -> SandboxResult:
        raise RuntimeError("호스트 인프라 오류")


def test_ct3_timeout_vs_infra_are_distinct_statuses() -> None:
    client_timeout = SandboxClient(TimeoutProvider())
    execution = client_timeout.run(_request())

    assert execution.result is None
    assert execution.status == "TIMEOUT"

    client_infra = SandboxClient(InfraProvider())
    execution_infra = client_infra.run(_request())

    assert execution_infra.result is None
    assert execution_infra.status == "INFRA_ERROR"
    assert execution.status != execution_infra.status


class GarbageProvider:
    name = "garbage"

    def execute(self, request: SandboxRequest) -> SandboxResult:
        # 유효하지 않은 결과 스키마를 반환한다.
        return SandboxResult.model_validate(
            {
                "result_id": "x",
                "request_id": "r1",
                "status": "UNKNOWN_STATUS",  # 유효하지 않은 상태
                "output_json": "not-a-dict",
            }
        )


def test_ct4_invalid_result_schema_not_promoted_to_evidence() -> None:
    client = SandboxClient(GarbageProvider())
    execution = client.run(_request())

    assert execution.status == "INFRA_ERROR"
    assert execution.evidence is None, "잘못된 결과가 ValidationEvidence 로 승격되지 않아야 한다"


class StaticProvider:
    """테스트용 공급자 — 요청 그대로 결과를 돌려준다."""

    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, request: SandboxRequest) -> SandboxResult:
        return _result(request_id=request.request_id, provider_name=self.name)


def test_ct5_provider_swap_does_not_change_orchestrator_code() -> None:
    def orchestrate(client: SandboxClient) -> SandboxExecutionStatus:
        return client.run(_request()).status

    client_a = SandboxClient(StaticProvider("local"))
    client_b = SandboxClient(StaticProvider("docker"))

    assert orchestrate(client_a) == "COMPLETED"
    assert orchestrate(client_b) == "COMPLETED"
    assert isinstance(client_a.provider, StaticProvider)
    assert isinstance(client_b.provider, StaticProvider)

    def orchestrate(client: SandboxClient) -> SandboxExecutionStatus:
        return client.run(_request()).status

    client_a = SandboxClient(StaticProvider("local"))
    client_b = SandboxClient(StaticProvider("docker"))

    assert orchestrate(client_a) == "COMPLETED"
    assert orchestrate(client_b) == "COMPLETED"
    assert isinstance(client_a.provider, StaticProvider)
    assert isinstance(client_b.provider, StaticProvider)

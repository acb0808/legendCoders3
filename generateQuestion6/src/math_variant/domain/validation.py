"""ValidationEvidence — 고정·샌드박스·블라인드 풀이·반례 검사 결과의 통합.

불변식:
- 미검증을 PASS 로 표현하는 경로가 없어야 한다. `status`는 필수이며 기본값이 없다.
- 반례(counterexample)가 있으면 상태는 PASS 일 수 없다. (T01.3-UT4)
- 직렬화 결과에 코드·입력·도구 버전 provenance 가 남는다. (T01.3-UT5)
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CheckStatus = Literal["PASS", "FAIL", "UNRESOLVED"]
CheckKind = Literal["fixed", "sandbox", "blind", "counterexample", "novelty", "scope"]


class CheckResult(BaseModel):
    """검사 하나의 결과."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    check_id: str
    kind: CheckKind
    status: CheckStatus
    critical: bool = False
    counterexample: dict[str, Any] | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    tool_version: str | None = None
    code_version: str | None = None
    provider_policy: str | None = None

    @model_validator(mode="after")
    def _counterexample_forbids_pass(self) -> CheckResult:
        if self.status == "PASS" and self.counterexample is not None:
            raise ValueError("반례(counterexample)가 있는 검사는 PASS 일 수 없다")
        return self


class ValidationEvidence(BaseModel):
    """후보 하나에 대한 검증 증거 집합."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(default="")
    candidate_id: str = Field(default="")
    checks: list[CheckResult] = Field(default_factory=list)
    code_version: str | None = None
    tool_versions: dict[str, str] = Field(default_factory=dict)
    input_hashes: dict[str, str] = Field(default_factory=dict)

    def passes(self) -> bool:
        return overall_status(self.checks) == "PASS"


def overall_status(checks: list[CheckResult]) -> CheckStatus:
    """증거 집합의 전체 상태를 집계한다.

    규칙 (실패 폐쇄):
    1. FAIL 이 하나라도 있으면 → FAIL
    2. critical UNRESOLVED 가 있으면 → UNRESOLVED
    3. UNRESOLVED 가 하나라도 있으면 → UNRESOLVED (판단 불능은 통과로 집계하지 않는다)
    4. 모두 PASS → PASS
    """
    if any(check.status == "FAIL" for check in checks):
        return "FAIL"
    if any(check.status == "UNRESOLVED" and check.critical for check in checks):
        return "UNRESOLVED"
    if any(check.status == "UNRESOLVED" for check in checks):
        return "UNRESOLVED"
    return "PASS"

"""T01.3 — ValidationEvidence 도메인 불변식 테스트.

- 미검증(UNRESOLVED) 상태를 PASS 로 표현하는 경로가 0건이어야 한다.
- CheckResult 가 PASS 일 때 반례가 존재하면 안 된다.
"""

from __future__ import annotations

from math_variant.domain.validation import CheckResult, ValidationEvidence, overall_status


def _check(status: str, **extra: object) -> CheckResult:
    return CheckResult(
        check_id=extra.pop("check_id", f"c-{status}"),
        kind=extra.pop("kind", "fixed"),
        status=status,  # type: ignore[arg-type]
        critical=extra.pop("critical", False),
        **extra,
    )


def test_unverified_is_never_represented_as_pass() -> None:
    checks = [
        _check("UNRESOLVED", check_id="a"),
        _check("PASS", check_id="b"),
    ]
    evidence = ValidationEvidence(checks=checks)

    assert evidence.passes() is False
    assert overall_status(evidence.checks) != "PASS"


def test_all_pass_is_pass() -> None:
    checks = [_check("PASS", check_id="a"), _check("PASS", check_id="b")]
    evidence = ValidationEvidence(checks=checks)

    assert evidence.passes() is True


def test_any_fail_is_fail_even_non_critical() -> None:
    checks = [
        _check("FAIL", check_id="novelty", critical=False),
        _check("PASS", check_id="scope", critical=True),
    ]
    evidence = ValidationEvidence(checks=checks)

    assert overall_status(evidence.checks) == "FAIL"
    assert evidence.passes() is False


def test_status_is_required() -> None:
    from pydantic import ValidationError

    try:
        CheckResult(check_id="x", kind="fixed", critical=True)  # type: ignore[call-arg]
    except ValidationError:
        pass
    else:  # pragma: no cover
        raise AssertionError("status 없이 CheckResult 가 생성되었다")


def test_counterexample_fail_passes_validator() -> None:
    result = CheckResult(
        check_id="c-ex",
        kind="counterexample",
        status="FAIL",
        critical=True,
        counterexample={"x": 0, "violation": "0으로 나눔"},
    )
    assert result.status == "FAIL"

"""T01.3 — TransformationPlan·CandidateProblem·ValidationEvidence 모델 테스트.

- T01.3-UT1: 변형 차원이 4개 미만이면 PLAN_CHANGE_DIMENSION_SHORTAGE다.
- T01.3-UT2: 구조적 변경이 2개 미만이면 계획을 거부한다.
- T01.3-UT3: critical UNRESOLVED가 있는 증거 집합은 PASS로 집계되지 않는다.
- T01.3-UT4: 반례가 있는 검사는 상태가 PASS일 수 없다.
- T01.3-UT5: 직렬화 결과에 코드·입력·도구 버전 provenance가 남는다.
"""

from __future__ import annotations

from math_variant.domain.candidate import CandidateProblem
from math_variant.domain.transformation import (
    Dimension,
    PlanValidationFailure,
    TransformationPlan,
    validate_plan,
)
from math_variant.domain.validation import CheckResult, ValidationEvidence, overall_status


def _minimal_plan(changed: list[Dimension]) -> TransformationPlan:
    return TransformationPlan(
        plan_id="plan-test",
        preserved_concepts=["원과 직선의 위치 관계", "접선"],
        changed_dimensions=changed,
        change_description=["숫자를 바꾼다"],
        rule_ids=["RULE_CIRCLE_CENTER_RADIUS"],
        construction_blueprint="중심·반지름 재표현 후 접선 조건",
        prohibited_patterns=[],
    )


def test_ut1_short_change_dimensions() -> None:
    changed = [Dimension.CONTEXT, Dimension.REPRESENTATION, Dimension.DATA_DOMAIN]

    plan = _minimal_plan(changed)
    failures = validate_plan(plan)

    assert any(f.code == "PLAN_CHANGE_DIMENSION_SHORTAGE" for f in failures), [
        f.model_dump() for f in failures
    ]


def test_ut2_structural_change_shortage_is_rejected() -> None:
    # 차원은 4개지만 전부 표면적(surface) 차원이면 구조적 변경 2개 미만이다.
    changed = [
        Dimension.CONTEXT,
        Dimension.REPRESENTATION,
        Dimension.DATA_DOMAIN,
        Dimension.CONDITION_ORDER,
    ]
    # CONDITION_ORDER 는 구조적 차원이므로 1개뿐인지 확인하고 테스트 전용으로 강제한다.
    structural = [d for d in changed if d.is_structural]
    assert len(structural) == 1

    plan = _minimal_plan(changed)
    failures = validate_plan(plan)

    assert any(f.code == "PLAN_STRUCTURAL_CHANGE_SHORTAGE" for f in failures), [
        f.model_dump() for f in failures
    ]


def test_ut3_critical_unresolved_is_not_pass() -> None:
    checks = [
        CheckResult(
            check_id="symbolic-main",
            kind="fixed",
            status="PASS",
            critical=True,
            evidence={"sympy_result": "True"},
        ),
        CheckResult(
            check_id="blind-a",
            kind="blind",
            status="UNRESOLVED",
            critical=True,
            evidence={"reason": "솔버 시간 초과"},
        ),
    ]
    evidence = ValidationEvidence(checks=checks)

    assert overall_status(evidence.checks) != "PASS"
    assert evidence.passes() is False


def test_ut4_counterexample_cannot_be_pass() -> None:
    try:
        CheckResult(
            check_id="fixed-answer",
            kind="fixed",
            status="PASS",
            critical=True,
            counterexample={"x": 2, "violation": "f(x) != 0"},
            evidence={"expr": "x**2-4"},
        )
    except ValueError as exc:
        assert "counterexample" in str(exc)
    else:  # pragma: no cover - 실패하면 오류가 나야 한다
        raise AssertionError("반례가 있는 검사가 PASS 로 생성되었다")


def test_ut5_serialization_keeps_provenance() -> None:
    evidence = ValidationEvidence(
        checks=[
            CheckResult(
                check_id="fixed-check",
                kind="fixed",
                status="PASS",
                critical=True,
                evidence={"input": "x**2 - 4"},
                tool_version="sympy 1.13.3",
                code_version="math_variant 0.1.0 sha123",
            )
        ]
    )
    candidate = CandidateProblem(
        candidate_id="cand-1",
        plan_id="plan-1",
        problem_text="문제 본문",
        formalization={"symbols": ["x"], "goal": "x=±2"},
        final_answer_claim="x=2 또는 x=-2",
        solution_steps=[{"step_id": "s1", "statement": "인수분해"}],
        transformation_evidence=[{"dimension": "representation"}],
    )

    data = evidence.model_dump()
    assert data["checks"][0]["tool_version"] == "sympy 1.13.3"
    assert data["checks"][0]["code_version"] == "math_variant 0.1.0 sha123"
    assert "status" in data["checks"][0]

    cand_data = candidate.model_dump()
    assert cand_data["verification_status"] != "PASS"
    assert cand_data["verification_status"] == "UNVERIFIED"


def test_plan_validation_failure_has_code() -> None:
    failure = PlanValidationFailure(code="PLAN_CHANGE_DIMENSION_SHORTAGE", message="차원 부족")
    assert failure.code == "PLAN_CHANGE_DIMENSION_SHORTAGE"

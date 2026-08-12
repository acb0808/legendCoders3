"""T04.6 — 승인된 계획별 문제 후보 생성기 테스트.

- T04.6-GT1: 후보의 formalization이 계획의 symbols·constraints·goal과 일치한다.
- T04.6-GT2: 문제 본문에 surface_blacklist 고위험 패턴이 나타나면 탈락한다.
- T04.6-GT3: 생성기가 계획 밖 개념을 추가하면 PLAN_DRIFT다.
- T04.6-GT4: final_answer_claim은 검증 상태 PASS를 자동 부여하지 않는다.
- T04.6-GT5: 통과 계획 수보다 많은 후보를 생성하지 않는다.
"""

from __future__ import annotations

from math_variant.domain.candidate import CandidateProblem
from math_variant.domain.problem import MathStatement, ProblemSpec
from math_variant.domain.scope import ScopeProfile
from math_variant.domain.transformation import Dimension, TransformationPlan
from math_variant.services.candidate_generator import (
    SURFACE_BLACKLIST,
    CandidateGenerator,
    validate_candidate_against_plan,
)

_SCOPE = ScopeProfile(
    profile_id="p1",
    school_name="테스트",
    exam_scope=["도형의 방정식"],
    allowed_units=["원의 방정식"],
    concept_vocabulary=["원", "직선", "접선", "좌표", "교점", "거리", "방정식"],
    allowed_answer_types=["expression"],
)

_PLAN = TransformationPlan(
    plan_id="plan-1",
    preserved_concepts=["원", "접선"],
    changed_dimensions=[
        Dimension.CONTEXT,
        Dimension.REPRESENTATION,
        Dimension.DATA_DOMAIN,
        Dimension.CONDITION_TOPOLOGY,
        Dimension.SOLUTION_ROUTE,
    ],
    change_description=["표현·상황·데이터를 바꾼다"],
    rule_ids=["RULE_TANGENT_DISTANCE"],
    construction_blueprint="외부 점에서 원에 그은 접선의 방정식",
)

_SPEC = ProblemSpec(
    spec_id="spec-1",
    source_text="점 (-6, 2)에서 원 x^2 + y^2 = 8에 그은 접선의 방정식을 구하시오.",
    curriculum_version="2022 개정",
    exam_scope=["도형의 방정식"],
    core_concepts=["원", "접선"],
    givens=[MathStatement(id="g", natural_language="원 x^2+y^2=8")],
    objective=MathStatement(id="goal", natural_language="접선의 방정식을 구하시오"),
    answer_type="expression",
    unknowns=[],
)


def _candidate(**overrides: object) -> CandidateProblem:
    base: dict = {
        "candidate_id": "cand-1",
        "plan_id": "plan-1",
        "problem_text": "점 (3, 4)에서 원 x^2 + y^2 = 25에 그은 접선의 방정식을 구하시오.",
        "formalization": {
            "symbols": ["x", "y"],
            "constraints": ["x^2 + y^2 - 25 = 0"],
            "goal": "접선의 방정식",
        },
        "final_answer_claim": "3x + 4y = 25",
        "solution_steps": [{"step_id": "s1", "statement": "거리 조건 사용"}],
        "transformation_evidence": [{"dimension": "representation"}],
    }
    base.update(overrides)
    return CandidateProblem(**base)


def test_gt1_formalization_matches_plan() -> None:
    candidate = _candidate()
    failures = validate_candidate_against_plan(candidate, _PLAN, _SPEC)

    assert failures == []


def test_gt2_surface_blacklist_pattern_rejected() -> None:
    candidate = _candidate(problem_text=f"원문 {SURFACE_BLACKLIST[0]} 을 이용하여 ...")
    failures = validate_candidate_against_plan(candidate, _PLAN, _SPEC)

    assert any(f.code == "SURFACE_BLACKLIST" for f in failures)


def test_gt3_out_of_plan_concept_is_plan_drift() -> None:
    candidate = _candidate(
        formalization={
            "symbols": ["x", "y", "z"],
            "constraints": ["x^2 + y^2 + z^2 = 0"],
            "goal": "로그의 값",
        }
    )
    failures = validate_candidate_against_plan(candidate, _PLAN, _SPEC)

    assert any(f.code == "PLAN_DRIFT" for f in failures)


def test_gt4_claim_does_not_auto_grant_pass() -> None:
    generator = CandidateGenerator(
        engine=None,  # type: ignore[arg-type]
        schemas=None,  # type: ignore[arg-type]
        scope=_SCOPE,
        style_profile={"school": "광문고", "tone": "서술형"},
    )
    candidate = generator.assemble_candidate(
        candidate_id="cand-4",
        plan=_PLAN,
        data={
            "problem_text": "문제 본문",
            "formalization": {
                "symbols": ["x", "y"],
                "constraints": [],
                "goal": "접선의 방정식",
            },
            "final_answer_claim": "3x + 4y = 25",
            "solution_steps": [],
            "transformation_evidence": [],
        },
    )

    assert candidate.verification_status != "PASS"
    assert candidate.verification_status == "UNVERIFIED"


def test_gt5_does_not_generate_more_than_passed_plans() -> None:
    class FakeEngine:
        def generate_structured(self, request, policy=None):
            from math_variant.providers.contracts import ProviderResponse

            return ProviderResponse(
                request_id=request.request_id,
                ok=True,
                data={
                    "problem_text": "문제 본문",
                    "formalization": {
                        "symbols": ["x", "y"],
                        "constraints": [],
                        "goal": "접선의 방정식",
                    },
                    "final_answer_claim": "답",
                    "solution_steps": [],
                    "transformation_evidence": [],
                },
            )

    generator = CandidateGenerator(
        engine=FakeEngine(),  # type: ignore[arg-type]
        schemas=None,  # type: ignore[arg-type]
        scope=_SCOPE,
        style_profile={},
    )
    plans = [_PLAN, _PLAN, _PLAN]  # 승인된 계획 3개

    candidates = generator.generate_all(_SPEC, plans)

    assert len(candidates) <= len(plans)
    assert len(candidates) == len(plans)

"""PipelineReport → RunStore 형식 변환 어댑터 (T08).

기존 검토 화면(public_run)은 verification_status=="PASS" + 필수 산출물(rubric, evidence)을
요구하므로, 파이프라인 후보를 그 형식에 맞춰 합성한다:
- rubric: 생성기의 solution_steps → RubricItem (score=1/단계)
- evidence: test_outcome(샌드박스) + blind_consensus → CheckResult
- critic 점수·코드리뷰 판정은 후보 메타데이터로 노출
"""

from __future__ import annotations

from typing import Any

from math_variant.agents.pipeline import CandidateVerdict, PipelineReport
from math_variant.domain.candidate import VerificationStatus


def report_to_run_store(report: PipelineReport) -> dict[str, Any]:
    """파이프라인 리포트를 RunStore 가 읽는 run JSON 으로 변환한다."""
    return {
        "run_id": report.run_id,
        "state": "GENERATED",
        "candidates": [_candidate_to_dict(v) for v in report.candidates],
        "created_at": report.created_at.isoformat(),
        "updated_at": report.created_at.isoformat(),
    }


def _verdict_to_status(status: str) -> VerificationStatus:
    """파이프라인 판정(Literal PASS/FAIL/UNRESOLVED/REVISE)을 저장 상태로 정규화한다."""
    if status == "PASS":
        return "PASS"
    if status == "FAIL":
        return "FAIL"
    return "UNRESOLVED"


def _candidate_to_dict(verdict: CandidateVerdict) -> dict[str, Any]:
    candidate = verdict.candidate
    status = _verdict_to_status(verdict.status)
    # 파이프라인의 판정(verdict.status)을 후보 상태로 반영해 저장된 run 과 일치시킨다.
    candidate.mark_verified(
        status, candidate.validation_ref or f"{candidate.candidate_id}:sandbox-test"
    )
    checks: list[dict[str, Any]] = []
    if verdict.test_outcome is not None:
        checks.append(
            {
                "check_id": f"{candidate.candidate_id}-sandbox",
                "kind": "sandbox",
                "status": "PASS" if verdict.test_outcome.passes else "FAIL",
                "critical": True,
                "evidence": {"detail": verdict.test_outcome.detail},
            }
        )
    if verdict.blind_consensus is not None:
        checks.append(
            {
                "check_id": f"{candidate.candidate_id}-blind",
                "kind": "blind",
                "status": "UNRESOLVED"
                if verdict.blind_consensus.status == "SOLVER_DISAGREEMENT"
                else verdict.blind_consensus.status,
                "critical": False,
                "evidence": {"reason": verdict.blind_consensus.reason},
            }
        )
    return {
        "candidate_id": candidate.candidate_id,
        "plan_id": candidate.plan_id,
        "problem_text": candidate.problem_text,
        "formalization": candidate.formalization.model_dump(mode="json"),
        "final_answer_claim": candidate.final_answer_claim,
        "solution_steps": [step.model_dump(mode="json") for step in candidate.solution_steps],
        "transformation_evidence": candidate.transformation_evidence,
        "verification_status": status,
        "validation_ref": candidate.validation_ref,
        "blueprint_title": verdict.blueprint_title,
        "critic_score": verdict.critic.score if verdict.critic else None,
        "code_review_verdict": verdict.code_review.verdict if verdict.code_review else None,
        "rubric": {
            "graph_id": f"{candidate.candidate_id}-rubric",
            "items": [
                {
                    "node_id": step.step_id,
                    "score": 1,
                    "description": step.statement,
                }
                for step in candidate.solution_steps
            ],
            "total_points": float(len(candidate.solution_steps)),
            "derived_from_verified": status == "PASS",
        },
        "evidence": {
            "evidence_id": f"{candidate.candidate_id}-evidence",
            "candidate_id": candidate.candidate_id,
            "checks": checks,
        },
    }

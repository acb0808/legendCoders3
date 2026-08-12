"""T08 — PipelineReport → RunStore 형식 변환 어댑터 테스트."""

from __future__ import annotations

import json

from math_variant.agents.pipeline import CandidateVerdict, PipelineReport
from math_variant.agents.schemas import CodeReviewOutput, CriticOutput, PlannerOutput
from math_variant.api.adapters import report_to_run_store
from math_variant.domain.candidate import CandidateProblem
from math_variant.sandbox.contracts import SandboxStatus
from math_variant.services.blind_solver import BlindConsensus
from math_variant.verifiers.test_runner import TestVerdict, VerificationOutcome


def _planner() -> PlannerOutput:
    return PlannerOutput.model_validate(
        {
            "core_concepts": ["포물선"],
            "auxiliary_concepts": [],
            "objective": "a의 값",
            "answer_type": "expression",
            "domain": "도형의 방정식",
            "preservation_goals": ["평행이동"],
            "strategy": {
                "difficulty_target": "중상",
                "preservation_goals": ["평행이동"],
                "variation_direction": ["질문 역전"],
                "quality_criteria": ["유일해"],
            },
            "unresolved_assumptions": [],
        }
    )


def _candidate(candidate_id: str, plan_id: str) -> CandidateProblem:
    return CandidateProblem(
        candidate_id=candidate_id,
        plan_id=plan_id,
        problem_text="문제 본문",
        formalization={"symbols": ["x"], "constraints": [], "goal": "a"},
        final_answer_claim="8sqrt(2)",
        solution_steps=[{"step_id": "s1", "statement": "단계"}],
        transformation_evidence=[{"dimension": "objective", "description": "역전"}],
    )


def _pass_verdict() -> CandidateVerdict:
    candidate = _candidate("cand-1", "plan-1")
    candidate.mark_verified("PASS", "run-1:sandbox-test")
    return CandidateVerdict(
        candidate=candidate,
        blueprint_title="질문 역전",
        code_review=CodeReviewOutput(verdict="APPROVE", safe=True, test_consistent=True),
        test_outcome=VerificationOutcome(
            verdict=TestVerdict.PASS,
            status=SandboxStatus.COMPLETED,
            detail="통과",
        ),
        blind_consensus=BlindConsensus(status="PASS", solver_a="A", solver_b="B"),
        critic=CriticOutput(score=8.0, difficulty_estimate="중상", recommendation="PASS"),
        status="PASS",
    )


def _fail_verdict() -> CandidateVerdict:
    candidate = _candidate("cand-2", "plan-2")
    candidate.mark_verified("FAIL", "run-2")
    return CandidateVerdict(
        candidate=candidate,
        blueprint_title="질문 역전",
        code_review=CodeReviewOutput(verdict="APPROVE", safe=True, test_consistent=True),
        test_outcome=VerificationOutcome(
            verdict=TestVerdict.FAIL,
            status=SandboxStatus.COMPLETED,
            detail="거짓 결과",
        ),
        blind_consensus=BlindConsensus(
            status="SOLVER_DISAGREEMENT", solver_a="A", solver_b="B", reason="해집합 상이"
        ),
        critic=CriticOutput(score=4.0, difficulty_estimate="중상", recommendation="REJECT"),
        status="FAIL",
    )


def test_report_to_run_store_maps_candidates() -> None:
    report = PipelineReport(
        run_id="run-1",
        planner=_planner(),
        ideas=[],
        adopted_ideas=[],
        candidates=[_pass_verdict()],
        ranking=[],
    )
    data = report_to_run_store(report)
    assert data["run_id"] == "run-1"
    assert data["state"] == "GENERATED"
    assert len(data["candidates"]) == 1
    candidate = data["candidates"][0]
    assert candidate["verification_status"] == "PASS"
    assert candidate["validation_ref"] == "run-1:sandbox-test"
    # 검토 화면(hasRequiredArtifacts)이 요구하는 산출물이 모두 있다
    assert candidate["solution_steps"]
    assert candidate["transformation_evidence"]
    assert candidate["rubric"]["items"]
    assert candidate["evidence"]["checks"]
    assert candidate["blueprint_title"] == "질문 역전"
    assert candidate["critic_score"] == 8.0
    checks = candidate["evidence"]["checks"]
    assert any(c["kind"] == "sandbox" and c["status"] == "PASS" and c["critical"] for c in checks)
    assert any(c["kind"] == "blind" for c in checks)
    # JSON 직렬화 가능 (RunStore.save_run 호환)
    json.dumps(data, ensure_ascii=False)


def test_report_to_run_store_non_pass_keeps_status() -> None:
    verdict = _fail_verdict()
    report = PipelineReport(
        run_id="run-2", planner=_planner(), ideas=[], adopted_ideas=[], candidates=[verdict]
    )
    data = report_to_run_store(report)
    assert data["candidates"][0]["verification_status"] == "FAIL"


def test_report_to_run_store_reject_maps_to_unresolved() -> None:
    candidate = _candidate("cand-3", "plan-3")
    verdict = CandidateVerdict(
        candidate=candidate,
        blueprint_title="질문 역전",
        code_review=CodeReviewOutput(verdict="REJECT", safe=False, test_consistent=False),
        test_outcome=None,
        blind_consensus=None,
        critic=CriticOutput(score=3.0, difficulty_estimate="중상", recommendation="REJECT"),
        status="UNRESOLVED",
    )
    report = PipelineReport(
        run_id="run-3", planner=_planner(), ideas=[], adopted_ideas=[], candidates=[verdict]
    )
    data = report_to_run_store(report)
    stored = data["candidates"][0]
    assert stored["verification_status"] == "UNRESOLVED"
    assert stored["validation_ref"] == "cand-3:sandbox-test"
    assert not any(c["kind"] == "sandbox" for c in stored["evidence"]["checks"])


def test_report_to_run_store_solver_disagreement_maps_to_unresolved() -> None:
    candidate = _candidate("cand-4", "plan-4")
    verdict = CandidateVerdict(
        candidate=candidate,
        blueprint_title="질문 역전",
        code_review=CodeReviewOutput(verdict="APPROVE", safe=True, test_consistent=True),
        test_outcome=VerificationOutcome(
            verdict=TestVerdict.PASS,
            status=SandboxStatus.COMPLETED,
            detail="통과",
        ),
        blind_consensus=BlindConsensus(
            status="SOLVER_DISAGREEMENT", solver_a="A", solver_b="B", reason="해집합 상이"
        ),
        critic=CriticOutput(score=7.0, difficulty_estimate="중상", recommendation="PASS"),
        status="PASS",
    )
    report = PipelineReport(
        run_id="run-4", planner=_planner(), ideas=[], adopted_ideas=[], candidates=[verdict]
    )
    data = report_to_run_store(report)
    stored = data["candidates"][0]
    assert stored["verification_status"] == "PASS"
    blind = next(c for c in stored["evidence"]["checks"] if c["kind"] == "blind")
    assert blind["status"] == "UNRESOLVED"

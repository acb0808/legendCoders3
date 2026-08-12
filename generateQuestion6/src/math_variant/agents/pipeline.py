"""다중 에이전트 병렬 파이프라인 오케스트레이터 (T07).

흐름:
  0. 기획(PLANNER) → 스펙·전략
  1. 발상(IDEATOR ×N 병렬, 고온) → 아이디어
  2. 선별(SELECTOR) → 채택 청사진
  3. 생성(GENERATOR ×N) → 후보 + 검증 스크립트 (+ 도형 필요 시 VISION)
  4. 검증(후보별): CODE_REVIEW → 샌드박스 실행 → BLIND A/B → CRITIC
  5. 집계(JUDGE) + 개선 루프(REVISE 재생성, 최대 max_refine 회)

원문 접근 경계: 원문 본문은 PLANNER 에만 전달된다.
후보의 PASS 는 "검증 스크립트가 샌드박스에서 PASS 판정"을 받을 때만 부여된다 (fail-closed).
"""

from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from math_variant.agents.code_reviewer import CodeReviewAgent
from math_variant.agents.critic import CriticAgent
from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.ideator import IdeatorAgent, build_ideation_brief
from math_variant.agents.judge import JudgeAgent
from math_variant.agents.planner import PlannerAgent
from math_variant.agents.schemas import (
    CodeReviewOutput,
    CriticOutput,
    IdeationOutput,
    PlannerOutput,
    ProductionStrategy,
)
from math_variant.agents.selector import SelectorAgent
from math_variant.agents.vision_artist import VisionArtist
from math_variant.domain.candidate import CandidateProblem
from math_variant.sandbox.provider import SandboxProvider
from math_variant.services.blind_solver import BlindConsensus
from math_variant.verifiers.test_runner import (
    VerificationOutcome,
    build_verification_request,
    run_verification,
)


class BlindPair(Protocol):
    """블라인드 합의 실행기 계약 (services.blind_solver.BlindSolver 를 충족한다)."""

    def solve_both(self, problem_text: str) -> BlindConsensus: ...


class CandidateVerdict(BaseModel):
    """후보 하나의 전체 검증 상태."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate: CandidateProblem
    blueprint_title: str
    code_review: CodeReviewOutput | None = None
    test_outcome: VerificationOutcome | None = None
    blind_consensus: BlindConsensus | None = None
    critic: CriticOutput | None = None
    attempts: int = 1
    status: Literal["PASS", "FAIL", "UNRESOLVED", "REVISE"] = "UNRESOLVED"


class PipelineReport(BaseModel):
    """파이프라인 실행 결과 컨테이너."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    planner: PlannerOutput
    ideas: list[IdeationOutput]
    adopted_ideas: list[str]
    candidates: list[CandidateVerdict]
    ranking: list[dict[str, Any]] = Field(default_factory=list)


def _to_strategy_dict(strategy: ProductionStrategy) -> dict[str, Any]:
    return {
        "difficulty_target": strategy.difficulty_target,
        "preservation_goals": strategy.preservation_goals,
        "variation_direction": strategy.variation_direction,
        "quality_criteria": strategy.quality_criteria,
        "constraints": strategy.constraints,
    }


class AgentPipeline:
    """역할 에이전트들을 병렬·순차로 오케스트레이션한다."""

    def __init__(
        self,
        planner: PlannerAgent,
        ideator: IdeatorAgent,
        selector: SelectorAgent,
        generator: GeneratorAgent,
        code_reviewer: CodeReviewAgent,
        critic: CriticAgent,
        judge: JudgeAgent,
        vision: VisionArtist | None,
        sandbox: SandboxProvider,
        blind_solvers: BlindPair,
        runs_dir: Path,
        ideator_count: int = 3,
        max_workers: int = 4,
        max_refine: int = 2,
    ) -> None:
        self.planner = planner
        self.ideator = ideator
        self.selector = selector
        self.generator = generator
        self.code_reviewer = code_reviewer
        self.critic = critic
        self.judge = judge
        self.vision = vision
        self.sandbox = sandbox
        self.blind_solvers = blind_solvers
        self.runs_dir = runs_dir
        self.ideator_count = ideator_count
        self.max_workers = max_workers
        self.max_refine = max_refine
        self.blind_calls = 0

    def run(self, source_text: str, strategy_brief: str = "") -> PipelineReport:
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        planner_out = self.planner.plan(source_text)
        strategy = _to_strategy_dict(planner_out.strategy)
        if not strategy_brief:
            strategy_brief = json.dumps(strategy, ensure_ascii=False)

        ideation_brief = build_ideation_brief(
            core_concepts=planner_out.core_concepts,
            objective=planner_out.objective,
            answer_type=planner_out.answer_type,
            domain=planner_out.domain,
            preservation_goals=planner_out.preservation_goals,
            strategy=planner_out.strategy,
        )
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            ideas = list(
                pool.map(
                    lambda seed: self.ideator.ideate(ideation_brief, seed=str(seed)),
                    range(self.ideator_count),
                )
            )
        selection = self.selector.select(ideas, strategy_brief)
        adopted = [i for i in ideas if i.idea_id in set(selection.adopted_ideas)]

        candidates = self._generate_and_verify(run_id, adopted, ideation_brief, strategy_brief)
        rank_entries = [
            {
                "candidate_id": v.candidate.candidate_id,
                "problem_text": v.candidate.problem_text,
                "test_pass": bool(v.test_outcome and v.test_outcome.passes),
                "blind": str(v.blind_consensus.status) if v.blind_consensus else "NONE",
                "critic_score": v.critic.score if v.critic else None,
                "attempts": v.attempts,
            }
            for v in candidates
        ]
        judge_out = self.judge.judge(rank_entries, run_id=run_id)
        ranking = judge_out.ranking if judge_out.ranking else rank_entries

        report = PipelineReport(
            run_id=run_id,
            planner=planner_out,
            ideas=ideas,
            adopted_ideas=selection.adopted_ideas,
            candidates=candidates,
            ranking=ranking,
        )
        self._write_report(run_id, report)
        return report

    def _generate_and_verify(
        self,
        run_id: str,
        blueprints: list[IdeationOutput],
        ideation_brief: str,
        strategy_brief: str,
    ) -> list[CandidateVerdict]:
        verdicts: list[CandidateVerdict] = []
        for index, blueprint in enumerate(blueprints):
            candidate_id = f"cand-{index + 1}"
            verdict = self._grow_candidate(
                run_id, candidate_id, blueprint, ideation_brief, strategy_brief
            )
            verdicts.append(verdict)
        return verdicts

    def _grow_candidate(
        self,
        run_id: str,
        candidate_id: str,
        blueprint: IdeationOutput,
        ideation_brief: str,
        strategy_brief: str,
        feedback: str = "",
        attempts: int = 1,
    ) -> CandidateVerdict:
        blueprint_dict = {
            "idea_id": blueprint.idea_id,
            "title": blueprint.title,
            "preserved_concepts": blueprint.preserved_concepts,
            "changed_dimensions": [d.value for d in blueprint.changed_dimensions],
            "construction_blueprint": blueprint.construction_blueprint,
        }
        candidate, extra = self.generator.generate(
            candidate_id=candidate_id,
            blueprint=blueprint_dict,
            brief=ideation_brief,
            feedback=feedback,
        )
        review = self.code_reviewer.review(
            extra.verification_script,
            candidate.problem_text,
            candidate.final_answer_claim,
            candidate_id=candidate_id,
        )
        test_outcome: VerificationOutcome | None = None
        if review.approves:
            request = build_verification_request(
                f"{run_id}-{candidate_id}-v{attempts}",
                extra.verification_script,
                problem_context={
                    "problem_text": candidate.problem_text,
                    "claimed_answer": candidate.final_answer_claim,
                },
            )
            test_outcome = run_verification(self.sandbox, request)
        consensus = self.blind_solvers.solve_both(candidate.problem_text)
        self.blind_calls += 1
        critic = self.critic.criticize(
            candidate.problem_text, ideation_brief, strategy_brief, candidate_id=candidate_id
        )

        if self.vision is not None and (extra.needs_figure or blueprint.figure_required):
            self.vision.render(
                candidate_id, extra.figure_notes or blueprint.figure_notes, candidate.problem_text
            )

        status: Literal["PASS", "FAIL", "UNRESOLVED", "REVISE"]
        needs_revision = review.verdict == "REVISE" or critic.recommendation == "REVISE"
        if test_outcome is not None and test_outcome.passes:
            status = "PASS"
            candidate.mark_verified("PASS", f"{run_id}:sandbox-test")
        elif review.verdict == "REJECT":
            status = "UNRESOLVED"
        elif needs_revision and attempts < self.max_refine:
            status = "REVISE"
        elif test_outcome is not None and test_outcome.verdict.value == "FAIL":
            status = "FAIL"
        else:
            status = "UNRESOLVED"

        if status == "REVISE":
            feedback = review.feedback or "; ".join(critic.comments)
            return self._grow_candidate(
                run_id,
                candidate_id,
                blueprint,
                ideation_brief,
                strategy_brief,
                feedback=feedback,
                attempts=attempts + 1,
            )

        verdict = CandidateVerdict(
            candidate=candidate,
            blueprint_title=blueprint.title,
            code_review=review,
            test_outcome=test_outcome,
            blind_consensus=consensus,
            critic=critic,
            attempts=attempts,
            status=status,
        )
        if test_outcome is not None and not test_outcome.passes:
            candidate.mark_verified("FAIL", run_id)
        return verdict

    def _write_report(self, run_id: str, report: PipelineReport) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        (self.runs_dir / "report.json").write_text(
            json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

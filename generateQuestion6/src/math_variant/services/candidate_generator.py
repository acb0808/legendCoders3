"""승인된 계획별 문제 후보 생성기 (T04.6).

입력 원칙: 생성기에는 승인 계획, ProblemSpec, 학교 문체 프로필만 전달하고
원문 전문과 주장 정답은 제외한다. 생성기의 답·해설은 검증 전 주장값으로 표시한다.

서버 검증:
- formalization 이 계획·스펙과 일치하지 않으면 실패 (PLAN_DRIFT)
- 문제 본문에 surface_blacklist 고위험 패턴이 있으면 탈락 (SURFACE_BLACKLIST)
- 계획 밖 개념 추가는 PLAN_DRIFT
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from math_variant.domain.candidate import (
    CandidateProblem,
    Formalization,
    SolutionStepClaim,
)
from math_variant.domain.problem import ProblemSpec
from math_variant.domain.scope import ScopeProfile
from math_variant.domain.transformation import TransformationPlan
from math_variant.errors import ErrorCode, StructuredError

# 문제 본문에서 복제·누출 신호가 되는 고위험 패턴
SURFACE_BLACKLIST: tuple[re.Pattern[str], ...] = (
    re.compile(r"원문", re.IGNORECASE),
    re.compile(r"다음 문항을 (복사|그대로)"),
    re.compile(r"출처"),
    re.compile(r"기출문제", re.IGNORECASE),
    re.compile(r"해설을 (참고|복사)"),
    re.compile(r"제시된 답"),
    re.compile(r"주관식 답안"),
)


class CandidateOutput(BaseModel):
    """LLM 응답 스키마 — 문제 본문과 기계 형식화·주장 답을 분리한다."""

    model_config = ConfigDict(extra="forbid")

    problem_text: str = Field(min_length=1)
    formalization: Formalization
    final_answer_claim: str = Field(min_length=1)
    solution_steps: list[SolutionStepClaim] = Field(default_factory=list)
    transformation_evidence: list[dict[str, Any]] = Field(default_factory=list)


class CandidateGenerator:
    """계획당 후보 하나를 생성하고 서버 검증을 적용한다."""

    def __init__(
        self,
        engine: Any,
        schemas: Any,
        scope: ScopeProfile,
        style_profile: dict[str, Any],
    ) -> None:
        self.engine = engine
        self.schemas = schemas
        self.scope = scope
        self.style_profile = style_profile

    def generate_all(
        self, spec: ProblemSpec, plans: list[TransformationPlan]
    ) -> list[CandidateProblem]:
        """승인 계획 수 이하로 후보를 생성한다. (GT5)"""
        candidates: list[CandidateProblem] = []
        for index, plan in enumerate(plans[: len(plans)]):
            if len(candidates) >= len(plans):
                break
            data = self._request_candidate(spec, plan, index)
            if data is None:
                continue
            candidate = self.assemble_candidate(
                candidate_id=f"cand-{index + 1}", plan=plan, data=data
            )
            candidates.append(candidate)
        return candidates

    def _request_candidate(
        self, spec: ProblemSpec, plan: TransformationPlan, index: int
    ) -> dict[str, Any] | None:
        if self.engine is None:
            return None
        prompt = self._build_prompt(spec, plan)
        from math_variant.providers.contracts import RolePolicy, StructuredRequest

        response = self.engine.generate_structured(
            StructuredRequest(
                request_id=f"candidate-{index}",
                role=RolePolicy.GENERATOR,
                prompt=prompt,
                response_schema="CandidateOutput",
            ),
            policy=None,
        )
        if not response.ok or response.data is None:
            return None
        data = response.data
        return data if isinstance(data, dict) else None

    def _build_prompt(self, spec: ProblemSpec, plan: TransformationPlan) -> str:
        # 원문 전문 대신 구조(스펙)와 승인 계획만 전달한다.
        return (
            f"[학교 문체] {self.style_profile}\n"
            f"[핵심 개념] {spec.core_concepts}\n"
            f"[목표] {spec.objective.natural_language}\n"
            f"[답 형태] {spec.answer_type}\n"
            f"[승인 계획] 보존={plan.preserved_concepts}, "
            f"변경 차원={[d.value for d in plan.changed_dimensions]}, "
            f"청사진={plan.construction_blueprint}\n"
            "원문 전체를 출력하지 말고 변형된 문제 본문만 생성하라."
        )

    def assemble_candidate(
        self, candidate_id: str, plan: TransformationPlan, data: dict[str, Any]
    ) -> CandidateProblem:
        """LLM 데이터를 CandidateProblem 으로 조립하고 검증한다."""
        output = CandidateOutput.model_validate(data)
        candidate = CandidateProblem(
            candidate_id=candidate_id,
            plan_id=plan.plan_id,
            problem_text=output.problem_text,
            formalization=output.formalization,
            final_answer_claim=output.final_answer_claim,
            solution_steps=output.solution_steps,
            transformation_evidence=output.transformation_evidence,
        )
        # 주장 답이 PASS 를 자동 부여하지 않는다: 상태는 UNVERIFIED 로 유지된다. (GT4)
        return candidate


def validate_candidate_against_plan(
    candidate: CandidateProblem,
    plan: TransformationPlan,
    spec: ProblemSpec,
) -> list[StructuredError]:
    """후보를 계획·스펙과 대조해 드리프트와 복제 패턴을 차단한다."""
    failures: list[StructuredError] = []

    # 계획 밖 개념/기호 (PLAN_DRIFT, GT3)
    allowed_symbols = _allowed_symbols(spec, plan)
    drifted = [sym for sym in candidate.formalization.symbols if sym not in allowed_symbols]
    if drifted:
        failures.append(
            StructuredError(
                code=ErrorCode.PLAN_DRIFT,
                message=f"계획 밖 기호 추가: {drifted}",
                context={"symbols": drifted},
            )
        )
    plan_dimensions = {d.value for d in plan.changed_dimensions}
    for evidence in candidate.transformation_evidence:
        dim = str(evidence.get("dimension", ""))
        if dim and dim not in plan_dimensions:
            failures.append(
                StructuredError(
                    code=ErrorCode.PLAN_DRIFT,
                    message=f"계획 밖 변형 차원: {dim}",
                    context={"dimension": dim},
                )
            )
    if candidate.formalization.goal and not _goal_consistent(candidate.formalization.goal, spec):
        failures.append(
            StructuredError(
                code=ErrorCode.PLAN_DRIFT,
                message=f"목표가 계획과 일치하지 않는다: {candidate.formalization.goal}",
            )
        )

    # surface blacklist (GT2)
    for pattern in SURFACE_BLACKLIST:
        if pattern.search(candidate.problem_text):
            failures.append(
                StructuredError(
                    code=ErrorCode.SURFACE_BLACKLIST,
                    message=f"문제 본문에 복제/누출 고위험 패턴 발견: {pattern.pattern}",
                )
            )
    return failures


def _allowed_symbols(spec: ProblemSpec, plan: TransformationPlan) -> set[str]:
    # 도형의 방정식 표준 변수 (기울기 m, 절편 k 등 포함)
    allowed = {"x", "y", "m", "k", "a", "b", "r", "p", "q"} | set(spec.unknowns)
    for given in spec.givens:
        if given.sympy_expr:
            allowed |= {ch for ch in given.sympy_expr if ch.isalpha()}
    return allowed


def _goal_consistent(goal: str, spec: ProblemSpec) -> bool:
    expected = spec.objective.natural_language
    if not expected:
        return True
    tokens = [t for t in re.split(r"[^가-힣]+", expected) if t]
    return any(token and token in goal for token in tokens[:2]) or goal in expected

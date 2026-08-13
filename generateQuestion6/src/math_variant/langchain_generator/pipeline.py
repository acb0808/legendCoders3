"""LangGraph 기반 전체 문제 생성 파이프라인 — 기존 AgentPipeline 의 드롭인 대체.

기존 httpx 파이프라인(`agents.pipeline.AgentPipeline`)의 전 단계를 LangGraph
StateGraph 로 옮긴 병행 모듈이다. 흐름은 기존과 동일하다:

    START → planner → ideate(×N 병렬) → select
          → generate(×채택 수, 유사도·REVISE 재시도 루프)
            → code_review → sandbox(APPROVE 시) → blind A/B → critic
            → vision(needs_figure 시) → verdict → emit
          → judge → report → END

기존 자산 재사용(이중 관리 금지):
- 역할 LLM 호출: 기존 에이전트 클래스 + `LangChainRoleEngine`(역할별 LCEL 체인)
- 프롬프트: `prompts/*.md` (기존 번들 그대로)
- 스키마: `agents/schemas.py`
- 유사도 필터·샌드박스 검증·블라인드 합의·보고서: 기존 서비스 그대로
"""

from __future__ import annotations

import json
import logging
import operator
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict, cast

from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command, Send
from pydantic import BaseModel

from math_variant.agents.blind import LLMBlindSolver
from math_variant.agents.code_reviewer import CodeReviewAgent
from math_variant.agents.critic import CriticAgent
from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.ideator import IdeatorAgent, build_ideation_brief
from math_variant.agents.judge import JudgeAgent
from math_variant.agents.pipeline import CandidateVerdict, PipelineReport, _to_strategy_dict
from math_variant.agents.planner import PlannerAgent
from math_variant.agents.schemas import (
    CodeReviewOutput,
    CriticOutput,
    GeneratorOutput,
    IdeationOutput,
    JudgeOutput,
    PlannerOutput,
    SelectionOutput,
    VisionOutput,
)
from math_variant.agents.selector import SelectorAgent
from math_variant.agents.vision_artist import VisionArtist
from math_variant.domain.candidate import CandidateProblem
from math_variant.errors import ErrorCode, MathVariantError, StructuredError
from math_variant.events import EventStage, PipelineEvent
from math_variant.langchain_generator.chains import build_structured_chain
from math_variant.langchain_generator.engine import LangChainRoleEngine
from math_variant.langchain_generator.settings import (
    LangChainLLMConfig,
    build_chat_model,
)
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.settings import ProviderSettings
from math_variant.reference.models import (
    ConditionPhrasing,
    ExamPatternCard,
    SolutionStyle,
)
from math_variant.reference.sections import (
    generator_condition_section,
    generator_style_section,
    ideator_pattern_section,
)
from math_variant.sandbox.provider import DockerSandboxProvider, SandboxProvider
from math_variant.services.blind_solver import BlindConsensus, BlindSolution, BlindSolver
from math_variant.verifiers.test_runner import (
    VerificationOutcome,
    build_verification_request,
    run_verification,
)

_LOGGER = logging.getLogger("math_variant.langchain_generator.pipeline")

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# 역할 → (시스템 프롬프트 파일, 응답 스키마) — 기존 역할 정책과 동일한 배치.
_ROLE_SPECS: dict[RolePolicy, tuple[str, type[BaseModel]]] = {
    RolePolicy.PLANNER: ("planner.md", PlannerOutput),
    RolePolicy.IDEATOR: ("ideator.md", IdeationOutput),
    RolePolicy.SELECTOR: ("selector.md", SelectionOutput),
    RolePolicy.GENERATOR: ("candidate_generator.md", GeneratorOutput),
    RolePolicy.CODE_REVIEWER: ("code_reviewer.md", CodeReviewOutput),
    RolePolicy.CRITIC: ("critic.md", CriticOutput),
    RolePolicy.JUDGE: ("judge.md", JudgeOutput),
    RolePolicy.BLIND_SOLVER: ("blind_solver.md", BlindSolution),
    RolePolicy.VISION: ("vision.md", VisionOutput),
}


@dataclass
class EventEmitter:
    """기존 AgentPipeline._emit 과 동일한 순번·형식으로 이벤트를 발행한다."""

    on_event: Callable[[PipelineEvent], None] | None
    seq: int = field(default=0)

    def emit(
        self,
        stage: EventStage,
        status: Literal["started", "done", "failed"],
        message: str = "",
        candidate_id: str | None = None,
    ) -> None:
        if self.on_event is None:
            return
        self.seq += 1
        self.on_event(
            PipelineEvent(
                event_id=f"stage-{self.seq}",
                type="stage",
                stage=stage,
                status=status,
                message=message,
                candidate_id=candidate_id,
            )
        )


@dataclass(frozen=True)
class PipelineContext:
    """모든 노드가 읽는 공유 컨텍스트 (langgraph context_schema).

    에이전트·검증기·설정은 실행 중 변하지 않으므로 context 로 분리해
    상태 채널을 오염시키지 않는다.
    """

    planner: PlannerAgent
    ideator: IdeatorAgent
    selector: SelectorAgent
    generator: GeneratorAgent
    code_reviewer: CodeReviewAgent
    critic: CriticAgent
    judge: JudgeAgent
    vision: VisionArtist | None
    sandbox: SandboxProvider
    blind_solvers: BlindSolver
    runs_dir: Path
    ideator_count: int
    max_refine: int
    emit: EventEmitter
    scope_section: str = ""
    critic_scope_section: str = ""
    reference_runnable: Runnable[dict[str, str], dict[str, Any]] | None = None


class PipelineState(TypedDict, total=False):
    """그래프 상태 — 기존 파이프라인의 실행 상태를 그대로 옮긴 것."""

    source_text: str
    difficulty_target: str
    strategy_brief: str
    run_id: str
    planner_out: PlannerOutput
    ideation_brief: str
    forbidden_structure: list[str]
    # 참조 자산 채널
    exam_patterns: list[ExamPatternCard]
    condition_refs: list[ConditionPhrasing]
    style_guide: SolutionStyle | None
    pattern_section: str
    condition_section: str
    style_section: str
    # 발상 팬아웃: 병렬 분기 결과를 병합하는 리듀서 채널
    seed: int
    ideas: Annotated[list[IdeationOutput], operator.add]
    adopted_blueprints: list[IdeationOutput]
    selection_out: SelectionOutput
    # 후보 팬아웃: 순차 처리 (기존 _generate_and_verify 의 for 루프와 동일한 의미)
    candidate_index: int
    blueprint: IdeationOutput
    candidate_id: str
    attempts: int
    feedback: str
    candidate: CandidateProblem
    generator_output: GeneratorOutput
    too_similar: bool
    failed: bool
    review: CodeReviewOutput
    test_outcome: VerificationOutcome
    consensus: BlindConsensus
    critic: CriticOutput
    verdict: CandidateVerdict
    verdicts: Annotated[list[CandidateVerdict], operator.add]
    ranking: list[dict[str, Any]]
    report: PipelineReport


def _planner_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    ctx = runtime.context
    ctx.emit.emit(EventStage.PLANNER, "started", "원문을 분석하여 변형 전략을 수립한다")
    planner_out = ctx.planner.plan(
        state["source_text"],
        difficulty_target=state.get("difficulty_target", ""),
        scope_section=ctx.scope_section,
    )
    ctx.emit.emit(EventStage.PLANNER, "done", "변형 스펙·전략 수립 완료")
    strategy_brief = state.get("strategy_brief", "")
    if not strategy_brief:
        strategy_brief = json.dumps(_to_strategy_dict(planner_out.strategy), ensure_ascii=False)
    ideation_brief = build_ideation_brief(
        core_concepts=planner_out.core_concepts,
        objective=planner_out.objective,
        answer_type=planner_out.answer_type,
        domain=planner_out.domain,
        preservation_goals=planner_out.preservation_goals,
        strategy=planner_out.strategy,
    )
    return {
        "run_id": f"run-{uuid.uuid4().hex[:8]}",
        "planner_out": planner_out,
        "strategy_brief": strategy_brief,
        "ideation_brief": ideation_brief,
        "forbidden_structure": planner_out.forbidden_structure,
    }


def _enrich_references_node(
    state: PipelineState, runtime: Runtime[PipelineContext]
) -> dict[str, Any]:
    ctx = runtime.context
    planner_out = state.get("planner_out")
    topics = ",".join(planner_out.core_concepts) if planner_out else ""
    if ctx.reference_runnable is not None and topics:
        ctx.emit.emit(
            EventStage.PLANNER, "started", "참조 자산(출제 패턴·조건 관례·해설 가이드) 검색"
        )
        ref_res = ctx.reference_runnable.invoke({"topics": topics})
        pats = ref_res.get("patterns", [])
        conds = ref_res.get("phrasings", [])
        style = ref_res.get("style")
        p_sec = ideator_pattern_section(pats)
        c_sec = generator_condition_section(conds)
        s_sec = generator_style_section(style)
        ctx.emit.emit(EventStage.PLANNER, "done", "참조 자산 주입 완료")
    else:
        pats = []
        conds = []
        style = None
        p_sec = ""
        c_sec = ""
        s_sec = ""

    return {
        "exam_patterns": pats,
        "condition_refs": conds,
        "style_guide": style,
        "pattern_section": p_sec,
        "condition_section": c_sec,
        "style_section": s_sec,
    }


def _dispatch_ideas(state: PipelineState, runtime: Runtime[PipelineContext]) -> Command[Any]:
    ctx = runtime.context
    ctx.emit.emit(EventStage.IDEATION, "started", f"변형 아이디어 {ctx.ideator_count}개 발상")
    # Send 의 arg 는 부모 상태를 상속하지 않는 분기 전용 상태이므로
    # 발상 분기에 필요한 키를 모두 실어 보낸다.
    return Command(
        goto=[
            Send(
                "ideate",
                {
                    "seed": index,
                    "ideation_brief": state["ideation_brief"],
                    "forbidden_structure": state["forbidden_structure"],
                    "pattern_section": state.get("pattern_section", ""),
                },
            )
            for index in range(ctx.ideator_count)
        ]
    )


def _ideate_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    # 기존과 동일하게 발상은 선택적이다 — 개별 실패는 삼키고 성공분만 수집한다.
    ctx = runtime.context
    try:
        idea = ctx.ideator.ideate(
            state["ideation_brief"],
            seed=str(state["seed"]),
            forbidden_structure=state["forbidden_structure"],
            pattern_section=state.get("pattern_section", ""),
        )
    except Exception as exc:
        _LOGGER.warning("ideator_skipped", extra={"error": str(exc)[:300]})
        return {"ideas": []}
    return {"ideas": [idea]}


def _select_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    ctx = runtime.context
    ideas = state.get("ideas", [])
    if not ideas:
        raise MathVariantError(
            StructuredError(
                code=ErrorCode.AGENT_UNRESOLVED,
                message="모든 발상자(ideator)가 아이디어를 생성하지 못했다",
                context={"ideator_count": ctx.ideator_count},
            )
        )
    ctx.emit.emit(EventStage.IDEATION, "done", f"발상 완료 ({len(ideas)}개)")
    ctx.emit.emit(EventStage.SELECTION, "started", "아이디어 채택 선별")
    selection = ctx.selector.select(ideas, state["strategy_brief"])
    adopted = [i for i in ideas if i.idea_id in set(selection.adopted_ideas)]
    ctx.emit.emit(EventStage.SELECTION, "done", f"채택 {len(adopted)}개")
    return {"selection_out": selection, "adopted_blueprints": adopted}


def _select_route(state: PipelineState, runtime: Runtime[PipelineContext]) -> str:
    return "dispatch" if state.get("adopted_blueprints") else "empty"


def _empty_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    runtime.context.emit.emit(EventStage.DONE, "failed", "채택된 아이디어가 없다")
    return {}


def _load_candidate(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    """채택된 청사진 중 다음 후보를 로드한다 (기존 _generate_and_verify 의 순차 루프)."""
    index = state.get("candidate_index", 0)
    blueprint = state["adopted_blueprints"][index]
    return {
        "blueprint": blueprint,
        "candidate_id": f"cand-{index + 1}",
        "attempts": 1,
        "feedback": "",
        "candidate_index": index,
    }


def _candidate_route(state: PipelineState, runtime: Runtime[PipelineContext]) -> str:
    """다음 후보 로드 여부 — 노드 진입 전에 판정해야 IndexError 없이 루프를 닫는다."""
    index = state.get("candidate_index", 0)
    return "load" if index < len(state["adopted_blueprints"]) else "judge"


def _blueprint_dict(blueprint: IdeationOutput) -> dict[str, Any]:
    """기존 AgentPipeline._grow_candidate 와 동일한 청사진 dict."""
    return {
        "idea_id": blueprint.idea_id,
        "title": blueprint.title,
        "preserved_concepts": blueprint.preserved_concepts,
        "changed_dimensions": [d.value for d in blueprint.changed_dimensions],
        "construction_blueprint": blueprint.construction_blueprint,
    }


def _generate_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    ctx = runtime.context
    ctx.emit.emit(EventStage.GENERATION, "started", "문제 생성", state["candidate_id"])
    try:
        candidate, output = ctx.generator.generate(
            candidate_id=state["candidate_id"],
            blueprint=_blueprint_dict(state["blueprint"]),
            brief=state["ideation_brief"],
            feedback=state.get("feedback", ""),
            forbidden_structure=state["forbidden_structure"],
            condition_section=state.get("condition_section", ""),
            style_section=state.get("style_section", ""),
        )
    except Exception as exc:
        _LOGGER.warning(
            "candidate_skipped",
            extra={"candidate": state["candidate_id"], "error": str(exc)[:300]},
        )
        return {"failed": True}

    from math_variant.services.similarity import similarity_report

    report = similarity_report(state["source_text"], candidate.problem_text)
    if report.too_similar:
        feedback = (
            f"[참신성 피드백] 원문과 '{report.match_snippet}' 구간이 일치합니다. "
            "같은 단원에서 이 구성과 다른 수학 아이디어로 문제를 다시 구성하세요."
        )
        ctx.emit.emit(
            EventStage.GENERATION,
            "failed",
            f"원문과 표현이 유사 (일치 {report.lcs_len}자) — 재생성",
            state["candidate_id"],
        )
        return {
            "candidate": candidate,
            "generator_output": output,
            "feedback": feedback,
            "too_similar": True,
        }
    ctx.emit.emit(EventStage.GENERATION, "done", "생성 완료", state["candidate_id"])
    return {"candidate": candidate, "generator_output": output, "too_similar": False}


def _generate_route(state: PipelineState, runtime: Runtime[PipelineContext]) -> str:
    if state.get("failed"):
        return "skip"
    if state.get("too_similar"):
        return "retry" if state["attempts"] < runtime.context.max_refine else "drop"
    return "review"


def _bump_attempts(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    return {"attempts": state["attempts"] + 1}


def _drop_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    _LOGGER.warning("candidate_similar", extra={"candidate": state["candidate_id"]})
    verdict = CandidateVerdict(
        candidate=state["candidate"],
        blueprint_title=state["blueprint"].title,
        attempts=state["attempts"],
        status="UNRESOLVED",
    )
    return {"verdicts": [verdict], "candidate_index": state["candidate_index"] + 1}


def _review_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    ctx = runtime.context
    ctx.emit.emit(EventStage.CODE_REVIEW, "started", "검증 스크립트 심사", state["candidate_id"])
    try:
        review = ctx.code_reviewer.review(
            state["generator_output"].verification_script,
            state["candidate"].problem_text,
            state["candidate"].final_answer_claim,
            candidate_id=state["candidate_id"],
        )
    except Exception as exc:
        _LOGGER.warning(
            "candidate_skipped",
            extra={"candidate": state["candidate_id"], "error": str(exc)[:300]},
        )
        return {"failed": True}
    ctx.emit.emit(EventStage.CODE_REVIEW, "done", f"심사: {review.verdict}", state["candidate_id"])
    return {"review": review}


def _review_route(state: PipelineState, runtime: Runtime[PipelineContext]) -> str:
    if state.get("failed"):
        return "skip"
    return "sandbox" if state["review"].approves else "blind"


def _sandbox_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    ctx = runtime.context
    ctx.emit.emit(EventStage.SANDBOX, "started", "샌드박스 검증 실행", state["candidate_id"])
    request = build_verification_request(
        f"{state['run_id']}-{state['candidate_id']}-v{state['attempts']}",
        state["generator_output"].verification_script,
        problem_context={
            "problem_text": state["candidate"].problem_text,
            "claimed_answer": state["candidate"].final_answer_claim,
        },
    )
    try:
        test_outcome = run_verification(ctx.sandbox, request)
    except Exception as exc:
        _LOGGER.warning(
            "candidate_skipped",
            extra={"candidate": state["candidate_id"], "error": str(exc)[:300]},
        )
        return {"failed": True}
    ctx.emit.emit(
        EventStage.SANDBOX, "done", f"검증: {test_outcome.verdict.value}", state["candidate_id"]
    )
    return {"test_outcome": test_outcome}


def _sandbox_route(state: PipelineState, runtime: Runtime[PipelineContext]) -> str:
    return "skip" if state.get("failed") else "blind"


def _blind_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    ctx = runtime.context
    ctx.emit.emit(EventStage.BLIND, "started", "블라인드 풀이 A·B", state["candidate_id"])
    try:
        consensus = ctx.blind_solvers.solve_both(state["candidate"].problem_text)
    except Exception as exc:
        _LOGGER.warning(
            "candidate_skipped",
            extra={"candidate": state["candidate_id"], "error": str(exc)[:300]},
        )
        return {"failed": True}
    ctx.emit.emit(EventStage.BLIND, "done", f"합의: {consensus.status}", state["candidate_id"])
    return {"consensus": consensus}


def _blind_route(state: PipelineState, runtime: Runtime[PipelineContext]) -> str:
    return "skip" if state.get("failed") else "critic"


def _critic_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    ctx = runtime.context
    ctx.emit.emit(EventStage.CRITIC, "started", "품질 비평", state["candidate_id"])
    try:
        critic = ctx.critic.criticize(
            state["candidate"].problem_text,
            state["ideation_brief"],
            state["strategy_brief"],
            candidate_id=state["candidate_id"],
            source_text=state["source_text"],
            forbidden_structure=state["forbidden_structure"],
            scope_section=ctx.critic_scope_section,
        )
    except Exception as exc:
        _LOGGER.warning(
            "candidate_skipped",
            extra={"candidate": state["candidate_id"], "error": str(exc)[:300]},
        )
        return {"failed": True}
    ctx.emit.emit(EventStage.CRITIC, "done", f"점수: {critic.score}", state["candidate_id"])
    return {"critic": critic}


def _critic_route(state: PipelineState, runtime: Runtime[PipelineContext]) -> str:
    if state.get("failed"):
        return "skip"
    needs_figure = runtime.context.vision is not None and (
        state["generator_output"].needs_figure or state["blueprint"].figure_required
    )
    return "vision" if needs_figure else "verdict"


def _vision_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    ctx = runtime.context
    try:
        ctx.vision.render(  # type: ignore[union-attr]
            state["candidate_id"],
            state["generator_output"].figure_notes or state["blueprint"].figure_notes,
            state["candidate"].problem_text,
        )
    except Exception as exc:
        _LOGGER.warning(
            "candidate_skipped",
            extra={"candidate": state["candidate_id"], "error": str(exc)[:300]},
        )
        return {"failed": True}
    return {}


def _vision_route(state: PipelineState, runtime: Runtime[PipelineContext]) -> str:
    return "skip" if state.get("failed") else "verdict"


def _verdict_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    ctx = runtime.context
    review = state["review"]
    critic = state["critic"]
    test_outcome = state.get("test_outcome")
    candidate = state["candidate"]

    needs_revision = review.verdict == "REVISE" or critic.recommendation == "REVISE"
    if test_outcome is not None and test_outcome.passes:
        status: Literal["PASS", "FAIL", "UNRESOLVED", "REVISE"] = "PASS"
        candidate.mark_verified("PASS", f"{state['run_id']}:sandbox-test")
    elif review.verdict == "REJECT":
        status = "UNRESOLVED"
    elif needs_revision and state["attempts"] < ctx.max_refine:
        status = "REVISE"
    elif test_outcome is not None and test_outcome.verdict.value == "FAIL":
        status = "FAIL"
    else:
        status = "UNRESOLVED"

    if status == "REVISE":
        feedback = (
            review.feedback
            or "; ".join(critic.comments)
            or "검증 스크립트를 수정하고 다시 생성하라"
        )
        return {
            "feedback": feedback,
            "verdict": _verdict(candidate, state, review, critic, test_outcome, status),
        }

    if test_outcome is not None and not test_outcome.passes:
        candidate.mark_verified("FAIL", state["run_id"])
    verdict = _verdict(candidate, state, review, critic, test_outcome, status)
    return {"verdict": verdict}


def _verdict(
    candidate: CandidateProblem,
    state: PipelineState,
    review: CodeReviewOutput,
    critic: CriticOutput,
    test_outcome: VerificationOutcome | None,
    status: Literal["PASS", "FAIL", "UNRESOLVED", "REVISE"],
) -> CandidateVerdict:
    return CandidateVerdict(
        candidate=candidate,
        blueprint_title=state["blueprint"].title,
        code_review=review,
        test_outcome=test_outcome,
        blind_consensus=state.get("consensus"),
        critic=critic,
        attempts=state["attempts"],
        status=status,
    )


def _verdict_route(state: PipelineState, runtime: Runtime[PipelineContext]) -> str:
    return "revise" if state["verdict"].status == "REVISE" else "emit"


def _emit_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    return {"verdicts": [state["verdict"]], "candidate_index": state["candidate_index"] + 1}


def _skip_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    return {"verdicts": [], "candidate_index": state["candidate_index"] + 1}


def _judge_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    ctx = runtime.context
    verdicts = state.get("verdicts", [])
    if not verdicts:
        raise MathVariantError(
            StructuredError(
                code=ErrorCode.AGENT_UNRESOLVED,
                message="모든 후보 생성·검증이 실패했다",
                context={"blueprint_count": len(state.get("adopted_blueprints", []))},
            )
        )
    rank_entries = [
        {
            "candidate_id": v.candidate.candidate_id,
            "problem_text": v.candidate.problem_text,
            "test_pass": bool(v.test_outcome and v.test_outcome.passes),
            "blind": str(v.blind_consensus.status) if v.blind_consensus else "NONE",
            "critic_score": v.critic.score if v.critic else None,
            "code_review": v.code_review.verdict if v.code_review else None,
            "attempts": v.attempts,
        }
        for v in verdicts
    ]
    ctx.emit.emit(EventStage.JUDGE, "started", "최종 랭킹 집계")
    judge_out = ctx.judge.judge(rank_entries, run_id=state["run_id"])
    ctx.emit.emit(EventStage.JUDGE, "done", "집계 완료")
    return {"ranking": judge_out.ranking if judge_out.ranking else rank_entries}


def _report_node(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    ctx = runtime.context
    verdicts = state.get("verdicts", [])
    report = PipelineReport(
        run_id=state["run_id"],
        planner=state["planner_out"],
        ideas=state.get("ideas", []),
        adopted_ideas=state["selection_out"].adopted_ideas,
        candidates=verdicts,
        ranking=state.get("ranking", []),
    )
    ctx.emit.emit(EventStage.DONE, "done", f"완료 — 후보 {len(report.candidates)}건")
    ctx.runs_dir.mkdir(parents=True, exist_ok=True)
    (ctx.runs_dir / "report.json").write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"report": report}


GraphT = StateGraph[PipelineState, PipelineContext, PipelineState, PipelineState]
CompiledGraphT = CompiledStateGraph[PipelineState, PipelineContext, PipelineState, PipelineState]


def _build_graph() -> GraphT:
    """전체 파이프라인 노드·엣지를 조립한다 (에이전트 주입 없음)."""
    graph = StateGraph(PipelineState, context_schema=PipelineContext)

    # 1) 기획 → 참조 자산 검색(풍부화) → 발상 팬아웃 → 선별
    graph.add_node("planner", _planner_node)
    graph.add_node("enrich_references", _enrich_references_node)
    graph.add_node("dispatch_ideas", _dispatch_ideas)
    graph.add_node("ideate", _ideate_node)
    graph.add_node("select", _select_node)
    graph.add_node("empty", _empty_node)

    # 2) 채택 후보 순차 루프 → 생성 → 검증 체인 → 판정 (기존 _generate_and_verify 와 동일)
    graph.add_node("load_candidate", _load_candidate)
    graph.add_node("generate", _generate_node)
    graph.add_node("bump_attempts", _bump_attempts)
    graph.add_node("drop", _drop_node)
    graph.add_node("code_review", _review_node)
    graph.add_node("sandbox", _sandbox_node)
    graph.add_node("blind", _blind_node)
    graph.add_node("critic", _critic_node)
    graph.add_node("vision", _vision_node)
    graph.add_node("verdict", _verdict_node)
    graph.add_node("emit_verdict", _emit_node)
    graph.add_node("skip", _skip_node)

    # 3) 집계 → 보고서
    graph.add_node("judge", _judge_node)
    graph.add_node("report", _report_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "enrich_references")
    graph.add_edge("enrich_references", "dispatch_ideas")
    graph.add_edge("ideate", "select")
    graph.add_conditional_edges(
        "select", _select_route, {"dispatch": "load_candidate", "empty": "empty"}
    )
    graph.add_edge("empty", "report")

    graph.add_edge("load_candidate", "generate")
    graph.add_conditional_edges(
        "generate",
        _generate_route,
        {"skip": "skip", "retry": "bump_attempts", "drop": "drop", "review": "code_review"},
    )
    graph.add_edge("bump_attempts", "generate")
    graph.add_conditional_edges(
        "drop", _candidate_route, {"load": "load_candidate", "judge": "judge"}
    )
    graph.add_conditional_edges(
        "code_review", _review_route, {"skip": "skip", "sandbox": "sandbox", "blind": "blind"}
    )
    graph.add_conditional_edges("sandbox", _sandbox_route, {"skip": "skip", "blind": "blind"})
    graph.add_conditional_edges("blind", _blind_route, {"skip": "skip", "critic": "critic"})
    graph.add_conditional_edges(
        "critic", _critic_route, {"skip": "skip", "vision": "vision", "verdict": "verdict"}
    )
    graph.add_conditional_edges("vision", _vision_route, {"skip": "skip", "verdict": "verdict"})
    graph.add_conditional_edges(
        "verdict", _verdict_route, {"revise": "bump_attempts", "emit": "emit_verdict"}
    )
    graph.add_conditional_edges(
        "emit_verdict", _candidate_route, {"load": "load_candidate", "judge": "judge"}
    )
    graph.add_conditional_edges(
        "skip", _candidate_route, {"load": "load_candidate", "judge": "judge"}
    )

    graph.add_edge("judge", "report")
    graph.add_edge("report", END)
    return graph


class LangChainPipeline:
    """컴파일된 LangGraph 파이프라인 — 기존 AgentPipeline.run 과 동일한 진입점.

    LangGraph 는 실행 컨텍스트(에이전트 등)를 invoke 시점 인자로 요구하므로,
    이 래퍼가 컨텍스트를 보관하고 `run(source_text, ...)` 만 노출한다.
    """

    def __init__(self, graph: CompiledGraphT, context: PipelineContext) -> None:
        self._graph = graph
        self._context = context

    @property
    def graph(self) -> CompiledGraphT:
        """시각화·검사용 컴파일 그래프."""
        return self._graph

    def run(
        self, source_text: str, strategy_brief: str = "", difficulty_target: str = ""
    ) -> PipelineReport:
        """원문 하나로 전체 파이프라인을 실행해 기존과 동일한 PipelineReport 를 반환한다."""
        result = self._graph.invoke(
            {
                "source_text": source_text,
                "strategy_brief": strategy_brief,
                "difficulty_target": difficulty_target,
            },
            context=self._context,
        )
        return cast(PipelineReport, result["report"])


def build_pipeline_graph(
    *,
    planner: PlannerAgent,
    ideator: IdeatorAgent,
    selector: SelectorAgent,
    generator: GeneratorAgent,
    code_reviewer: CodeReviewAgent,
    critic: CriticAgent,
    judge: JudgeAgent,
    vision: VisionArtist | None,
    sandbox: SandboxProvider,
    blind_solvers: BlindSolver,
    runs_dir: Path,
    ideator_count: int = 3,
    max_refine: int = 2,
    on_event: Callable[[PipelineEvent], None] | None = None,
    scope_section: str = "",
    critic_scope_section: str = "",
    reference_runnable: Runnable[dict[str, str], dict[str, Any]] | None = None,
) -> LangChainPipeline:
    """주입된 에이전트·검증기로 컴파일된 파이프라인을 만든다.

    테스트는 가짜 엔진 기반 에이전트를 주입해 네트워크 없이 전체 흐름을
    검증할 수 있다 (기존 tests/unit/agents/test_pipeline.py 와 동일한 패턴).
    """
    context = PipelineContext(
        planner=planner,
        ideator=ideator,
        selector=selector,
        generator=generator,
        code_reviewer=code_reviewer,
        critic=critic,
        judge=judge,
        vision=vision,
        sandbox=sandbox,
        blind_solvers=blind_solvers,
        runs_dir=runs_dir,
        ideator_count=ideator_count,
        max_refine=max_refine,
        emit=EventEmitter(on_event),
        scope_section=scope_section,
        critic_scope_section=critic_scope_section,
        reference_runnable=reference_runnable,
    )
    return LangChainPipeline(_build_graph().compile(), context)


def build_langchain_pipeline(
    *,
    ideator_count: int = 3,
    max_refine: int = 2,
    on_event: Callable[[PipelineEvent], None] | None = None,
    runs_dir: Path,
    figures_dir: Path,
    sandbox_image: str = "math-variant-sandbox:test",
    forbidden_context: dict[str, str] | None = None,
    scope_section: str = "",
    critic_scope_section: str = "",
    reference_runnable: Runnable[dict[str, str], dict[str, Any]] | None = None,
) -> LangChainPipeline:
    """설정·역할 체인·에이전트를 묶어 LangChain 파이프라인 그래프를 구성한다.

    기존 pipeline_factory.build_agent_pipeline 과 동일한 구성(역할 정책·프롬프트
    번들·샌드박스·블라인드 합의)을 사용하되, LLM 호출 계층만 LangChain 체인으로
    교체한다. 실제 LLM 호출은 graph.invoke() 시점에 발생한다.
    """
    settings = ProviderSettings()
    role_entries = settings.role_policy().roles
    llm_cache: dict[str, ChatOpenAI] = {}

    def _llm_for(provider_name: str, model_name: str) -> ChatOpenAI:
        cache_key = f"{provider_name}:{model_name}"
        llm = llm_cache.get(cache_key)
        if llm is None:
            if provider_name == "openai":
                config = LangChainLLMConfig(
                    provider="openai",
                    model=model_name,
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                )
            else:
                config = LangChainLLMConfig(
                    provider=provider_name,
                    model=model_name,
                    api_key=settings.deepseek_api_key,
                    base_url=settings.deepseek_base_url,
                )
            llm = build_chat_model(config)
            llm_cache[cache_key] = llm
        return llm

    def _prompt(name: str) -> str:
        return (PROMPTS_DIR / name).read_text(encoding="utf-8")

    chains: dict[RolePolicy, Runnable[dict[str, str], Any]] = {}
    fallback_chains: dict[RolePolicy, Runnable[dict[str, str], Any]] = {}
    for role, (md_name, schema) in _ROLE_SPECS.items():
        entry = role_entries[role]
        chains[role] = build_structured_chain(
            _llm_for(entry.provider, entry.model),
            system_md=_prompt(md_name),
            output_model=schema,
            include_raw=True,
        )
        if entry.fallback_provider and entry.fallback_model:
            fallback_chains[role] = build_structured_chain(
                _llm_for(entry.fallback_provider, entry.fallback_model),
                system_md=_prompt(md_name),
                output_model=schema,
                include_raw=True,
            )

    engine = LangChainRoleEngine(
        chains=chains,
        fallback_chains=fallback_chains if fallback_chains else None,
        on_event=on_event,
    )

    blind_a = LLMBlindSolver(engine, _prompt("blind_solver.md"), "A")
    blind_b = LLMBlindSolver(engine, _prompt("blind_solver.md"), "B")
    blind_solvers = BlindSolver(blind_a, blind_b, forbidden_context or {})

    graph = build_pipeline_graph(
        planner=PlannerAgent(engine, _prompt("planner.md")),
        ideator=IdeatorAgent(engine, _prompt("ideator.md")),
        selector=SelectorAgent(engine, _prompt("selector.md")),
        generator=GeneratorAgent(engine, _prompt("candidate_generator.md")),
        code_reviewer=CodeReviewAgent(engine, _prompt("code_reviewer.md")),
        critic=CriticAgent(engine, _prompt("critic.md")),
        judge=JudgeAgent(engine, _prompt("judge.md")),
        vision=VisionArtist(engine, _prompt("vision.md"), figures_dir),
        sandbox=DockerSandboxProvider(image=sandbox_image),
        blind_solvers=blind_solvers,
        runs_dir=runs_dir,
        ideator_count=ideator_count,
        max_refine=max_refine,
        on_event=on_event,
        scope_section=scope_section,
        critic_scope_section=critic_scope_section,
        reference_runnable=reference_runnable,
    )
    return graph

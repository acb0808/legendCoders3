"""LangChain 모듈과 기존 httpx 파이프라인의 동일성(패리티) 검증 스크립트.

동일한 입력(원문·난이도·seed)과 동일한 LLM 응답 데이터로 양쪽을 실행해
1) 프롬프트 번들 로딩, 2) 입력 섹션 포맷, 3) 승인 청사진 dict, 4) CandidateProblem
조립, 5) 시스템 메시지(JSON 지시) 주입이 서로 같은지 확인한다.
LLM 네트워크 호출은 하지 않는다.

사용법: .venv/Scripts/python scratch/verify_parity.py
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda

from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.ideator import IdeatorAgent, build_ideation_brief
from math_variant.agents.planner import PlannerAgent
from math_variant.agents.schemas import (
    GeneratorOutput,
    IdeationOutput,
    PlannerOutput,
)
from math_variant.langchain_generator.chains import JSON_SYSTEM_MESSAGE, build_structured_chain
from math_variant.langchain_generator.generator import (
    PROMPTS_DIR,
    LangChainProblemGenerator,
)
from math_variant.langchain_generator.settings import build_chat_model, resolve_llm_config
from math_variant.providers.base import ModelPolicy
from math_variant.providers.contracts import ProviderResponse, StructuredRequest
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine

_PLANNER_DATA: dict[str, Any] = {
    "core_concepts": ["원", "직선의 위치 관계"],
    "auxiliary_concepts": ["접점"],
    "objective": "상수의 범위를 구하시오",
    "answer_type": "interval",
    "domain": "도형의 방정식",
    "preservation_goals": ["원과 직선의 위치 관계"],
    "forbidden_structure": ["접선의 방정식 구성", "거리 = 반지름 조건"],
    "strategy": {
        "difficulty_target": "중상",
        "preservation_goals": ["원과 직선의 위치 관계"],
        "variation_direction": ["질문 역전", "조건 위상 변경"],
        "quality_criteria": ["유일해"],
        "constraints": [],
    },
    "unresolved_assumptions": [],
}

_IDEA_DATA: dict[str, Any] = {
    "idea_id": "idea-7",
    "title": "할선 상황으로 재구성",
    "preserved_concepts": ["원", "직선"],
    "changed_dimensions": ["objective", "condition_topology"],
    "change_description": ["접선 상황을 두 점에서 만나는 직선 상황으로 바꾼다"],
    "construction_blueprint": "판별식 D>0 경로로 k의 범위를 도출",
    "figure_required": False,
    "figure_notes": "",
}

_GENERATOR_DATA: dict[str, Any] = {
    "problem_text": "원과 직선이 서로 다른 두 점에서 만나도록 하는 k의 범위를 구하시오.",
    "formalization": {
        "symbols": ["k"],
        "constraints": ["D>0"],
        "goal": "k의 범위",
        "domain": "도형의 방정식",
    },
    "final_answer_claim": "-5<k<5",
    "solution_steps": [{"step_id": "s1", "statement": "판별식을 계산한다"}],
    "transformation_evidence": [{"dimension": "objective", "description": "질문 역전"}],
    "verification_script": "print('ok')",
    "needs_figure": False,
    "figure_notes": "",
}

_SOURCE = "원 x^2+y^2=25 위의 점 (3,4) 에서의 접선의 방정식을 구하시오."
_DIFFICULTY = "중상"
_SEED = "cand-1"


class _CaptureEngine(StructuredOutputEngine):
    """역할별 고정 응답과 프롬프트 캡처를 제공하는 테스트 엔진 (기존 파이프라인용)."""

    def __init__(self, data: dict[str, dict[str, Any]]) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self._data = data
        self.prompts: list[str] = []

    def generate_structured(
        self, request: StructuredRequest, policy: ModelPolicy | None
    ) -> ProviderResponse:
        self.prompts.append(request.prompt)
        return ProviderResponse(
            request_id=request.request_id, ok=True, data=self._data[request.role.value]
        )


def _fake_chain(output: Any, calls: list[dict[str, str]]) -> Runnable[dict[str, str], Any]:
    """고정 응답을 반환하고 입력을 캡처하는 가짜 체인 (LangChain 모듈용)."""

    def _run(payload: dict[str, str]) -> Any:
        calls.append(payload)
        return output

    return RunnableLambda(_run)


def _existing_flow() -> tuple[list[str], Any]:
    """기존 httpx 파이프라인 에이전트 3종으로 흐름을 실행하고 프롬프트·후보를 돌려준다."""
    engine = _CaptureEngine(
        {"planner": _PLANNER_DATA, "ideator": _IDEA_DATA, "generator": _GENERATOR_DATA}
    )

    def _bundle(name: str) -> str:
        return (PROMPTS_DIR / name).read_text(encoding="utf-8")

    planner = PlannerAgent(engine, _bundle("planner.md"))
    ideator = IdeatorAgent(engine, _bundle("ideator.md"))
    generator = GeneratorAgent(engine, _bundle("candidate_generator.md"))

    plan = planner.plan(_SOURCE, difficulty_target=_DIFFICULTY)
    brief = build_ideation_brief(
        core_concepts=plan.core_concepts,
        objective=plan.objective,
        answer_type=plan.answer_type,
        domain=plan.domain,
        preservation_goals=plan.preservation_goals,
        strategy=plan.strategy,
    )
    idea = ideator.ideate(brief, seed="idea-7", forbidden_structure=plan.forbidden_structure)
    blueprint = {
        "idea_id": idea.idea_id,
        "title": idea.title,
        "preserved_concepts": idea.preserved_concepts,
        "changed_dimensions": [d.value for d in idea.changed_dimensions],
        "construction_blueprint": idea.construction_blueprint,
    }
    candidate, _output = generator.generate(
        candidate_id=_SEED,
        blueprint=blueprint,
        brief=brief,
        feedback="",
        forbidden_structure=plan.forbidden_structure,
    )
    return engine.prompts, candidate


def _langchain_flow() -> tuple[list[dict[str, str]], Any]:
    """LangChain 모듈로 같은 흐름을 실행하고 입력 캡처·결과를 돌려준다."""
    plan = PlannerOutput.model_validate(_PLANNER_DATA)
    idea = IdeationOutput.model_validate(_IDEA_DATA)
    output = GeneratorOutput.model_validate(_GENERATOR_DATA)
    calls: dict[str, list[dict[str, str]]] = {"planner": [], "ideator": [], "generator": []}
    generator = LangChainProblemGenerator(
        planner_chain=_fake_chain(plan, calls["planner"]),
        ideator_chain=_fake_chain(idea, calls["ideator"]),
        generator_chain=_fake_chain(output, calls["generator"]),
    )
    result = generator.generate(_SOURCE, difficulty_target=_DIFFICULTY, seed=_SEED)
    return [calls["planner"][0], calls["ideator"][0], calls["generator"][0]], result.candidate


def _check(label: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {label}" + (f" — {detail}" if detail and not ok else ""))
    return ok


def main() -> int:
    """양쪽 흐름을 실행하고 동일성 체크 목록을 출력한다."""
    bundle = {
        "planner": (PROMPTS_DIR / "planner.md").read_text(encoding="utf-8"),
        "ideator": (PROMPTS_DIR / "ideator.md").read_text(encoding="utf-8"),
        "generator": (PROMPTS_DIR / "candidate_generator.md").read_text(encoding="utf-8"),
    }
    ok = True

    # 1) 프롬프트 번들: 기존 pipeline_factory 와 같은 디렉터리에서 읽는가
    from math_variant.pipeline_factory import PROMPTS_DIR as PIPELINE_PROMPTS_DIR

    same_dir = PROMPTS_DIR == PIPELINE_PROMPTS_DIR
    ok = _check(
        "프롬프트 번들 경로 일치 (pipeline_factory.PROMPTS_DIR 와 동일)",
        same_dir,
        f"LangChain={PROMPTS_DIR} vs 기존={PIPELINE_PROMPTS_DIR}",
    ) and ok

    # 2) 시스템 메시지: 기존 어댑터의 JSON 지시 + 역할 md 분해가 동일한가
    config = resolve_llm_config()
    chain = build_structured_chain(
        build_chat_model(config), system_md=bundle["planner"], output_model=PlannerOutput
    )
    system_text = str(chain.get_prompts()[0].format_messages(input="x")[0].content)
    expected_system = f"{JSON_SYSTEM_MESSAGE}\n\n{bundle['planner']}"
    ok = _check("시스템 메시지 = JSON 지시 + 역할 md (기존 openai_adapter 와 동일 문구)",
                system_text == expected_system) and ok
    ok = _check("JSON 지시 문구가 기존 어댑터와 일치",
                JSON_SYSTEM_MESSAGE == "You must respond in JSON format only.") and ok

    existing_prompts, existing_candidate = _existing_flow()
    langchain_inputs, langchain_candidate = _langchain_flow()
    roles = ["planner", "ideator", "generator"]
    labels = {
        "planner": "planner ([원문] + [난이도 목표])",
        "ideator": "ideator ([입력] + [금지 구조])",
        "generator": "generator ([문제 구조] + [승인 청사진] + [금지 구조])",
    }

    # 3) 입력 섹션 포맷: 기존 user 프롬프트 == 번들 + "\n\n" + LangChain human 입력
    for index, role in enumerate(roles):
        existing = existing_prompts[index]
        human = langchain_inputs[index]["input"]
        ok = _check(
            f"{labels[role]} 입력 포맷 일치 (bundle + blank + human)",
            existing == f"{bundle[role]}\n\n{human}",
            f"기존={existing[:80]!r} vs LangChain={human[:80]!r}",
        ) and ok

    # 4) 원문 분리: ideator 이후 입력에 원문 본문이 없는가 (양쪽)
    ok = _check(
        "원문 분리 원칙 (ideator/generator 입력에 원문 없음)",
        _SOURCE not in langchain_inputs[1]["input"]
        and _SOURCE not in langchain_inputs[2]["input"]
        and _SOURCE not in existing_prompts[1]
        and _SOURCE not in existing_prompts[2],
    ) and ok

    # 5) 후보 조립: CandidateProblem 필드가 동일한가 (status 제외 비교)
    lc = langchain_candidate.model_dump()
    ex = existing_candidate.model_dump()
    ok = _check(
        "CandidateProblem 조립 동일 (problem_text·formalization·답·풀이·근거)",
        all(lc[key] == ex[key] for key in (
            "candidate_id", "plan_id", "problem_text", "formalization",
            "final_answer_claim", "solution_steps", "transformation_evidence",
        )),
        f"LangChain={lc.get('candidate_id')}/{lc.get('plan_id')} vs "
        f"기존={ex.get('candidate_id')}/{ex.get('plan_id')}",
    ) and ok

    print("=" * 70)
    print("결과:", "모든 체크 통과 - LangChain 모듈은 기존 파이프라인과 동일하게 동작한다" if ok
          else "불일치 발견 - 위 FAIL 항목을 확인하라")
    return 0 if ok else 1


if __name__ == "__main__":  # pragma: no cover - 스크래치 검증 도구
    raise SystemExit(main())

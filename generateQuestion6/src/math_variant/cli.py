"""로컬 품질 게이트 CLI (T00.1).

사용법:
  math-variant gate            # 선언된 품질 명령을 순차 실행
  math-variant check-locks     # 의존성 잠금 파일 검사
  math-variant run [시험지] [문항]  # 다중 에이전트 파이프라인 실행 (기본: 광명북고 2023 Q19)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from math_variant.tooling.quality import BACKEND_GATES, FRONTEND_GATES, check_dependency_locks

REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SOURCE = "시험지/[2023년 기출] 광명북고1-2 중간 (주)_structured.json"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _argv(command: str) -> list[str]:
    """품질 명령을 실행 가능한 argv 로 변환한다.

    ruff/mypy/pytest 는 반드시 현재 venv 의 python(sys.executable)로 실행해
    시스템 python 과 혼동되지 않게 한다. npm 은 Windows 에서 cmd 를 통해 실행한다.
    """
    parts = command.split()
    tool = parts[0]
    if tool in {"ruff", "mypy", "pytest"}:
        return [sys.executable, "-m", *parts]
    if tool == "npm":
        return ["cmd", "/c", command]
    return parts


def _run(command: str, cwd: Path) -> bool:
    argv = _argv(command)
    print(f"\n$ {' '.join(argv)}  ({cwd})")
    result = subprocess.run(argv, cwd=cwd, check=False)  # noqa: S603
    if result.returncode != 0:
        print(f"  FAILED (exit {result.returncode})")
    else:
        print("  OK")
    return result.returncode == 0


def run_gates() -> int:
    ok = True
    ok = _run(BACKEND_GATES[0].command, REPO_ROOT) and ok
    ok = _run(BACKEND_GATES[1].command, REPO_ROOT) and ok
    ok = _run(BACKEND_GATES[2].command, REPO_ROOT) and ok
    ok = _run(BACKEND_GATES[3].command, REPO_ROOT) and ok
    for gate in FRONTEND_GATES:
        ok = _run(gate.command, REPO_ROOT / gate.working_directory) and ok
    return 0 if ok else 1


def check_locks() -> int:
    report = check_dependency_locks(REPO_ROOT)
    for failure in report.failures:
        print(str(failure.as_error()), file=sys.stderr)
    return 0 if report.ok else 1


def run_demo() -> int:
    """실제 시험지 원문에서 변형 문항을 만들어 출력한다 (오프라인 파이프라인 데모)."""
    import json

    from math_variant.domain.problem import MathStatement, ProblemSpec
    from math_variant.domain.scope import ScopeProfile
    from math_variant.domain.solution import Rubric, RubricItem
    from math_variant.domain.transformation import (
        Dimension,
        TransformationPlan,
        validate_plan,
    )
    from math_variant.rules.geometry import build_geometry_catalog
    from math_variant.services.baseline_solver import BaselineSolver
    from math_variant.services.candidate_generator import validate_candidate_against_plan
    from math_variant.services.geometry_parser import DeterministicSourceAnalyzer
    from math_variant.services.normalize import normalize_source
    from math_variant.services.variation_engine import VariationEngine
    from math_variant.verifiers.source_gate import SourceGate

    scope = ScopeProfile(
        profile_id="demo",
        school_name="광문고",
        exam_scope=["도형의 방정식"],
        allowed_units=["좌표와 직선", "원의 방정식", "도형의 이동"],
        concept_vocabulary=[
            "좌표",
            "직선",
            "원",
            "접선",
            "평행이동",
            "대칭이동",
            "교점",
            "거리",
            "중점",
            "방정식",
        ],
        allowed_answer_types=["expression", "interval", "coordinate"],
    )

    source_path = REPO_ROOT / "시험지" / "[2018년 기출] 광문고1-2 중간 (주)_structured.json"
    questions = json.loads(source_path.read_text(encoding="utf-8"))
    source = next(q for q in questions if str(q["question_number"]) == "21")
    raw_text = source["question_text"]
    text = normalize_source(raw_text)

    # 1) 원문 분석
    analyzer = DeterministicSourceAnalyzer(scope)
    spec = analyzer.analyze(text)

    # 2) 원문 독립 풀이 + Source Gate
    solver = BaselineSolver(scope)
    baseline = solver.solve(spec)
    gate = SourceGate().evaluate(spec, baseline)

    # 3) 변형 계획 (규칙 카탈로그 기반 — 실제 적용할 구조적 차원과 일치)
    catalog = build_geometry_catalog(scope)
    rule_ids = [
        "RULE_OBJECTIVE_INVERSION",  # 질문 역전 (접선 방정식 → k의 범위/중심 거리)
        "RULE_CONDITION_TOPOLOGY",  # 조건 위상 (접점 1개 → 교점 2개 상황)
        "RULE_TANGENT_DISCRIMINANT",  # 풀이 경로 (거리 → 판별식)
    ]
    catalog.validate_combination(rule_ids)
    plan = TransformationPlan(
        plan_id="plan-demo",
        preserved_concepts=["원", "직선의 위치 관계"],
        changed_dimensions=[
            Dimension.OBJECTIVE,
            Dimension.CONDITION_TOPOLOGY,
            Dimension.SOLUTION_ROUTE,
            Dimension.DATA_DOMAIN,
        ],
        change_description=[
            "접선의 방정식 → 두 점에서 만나도록 하는 k의 범위 (질문 역전)",
            "접점 1개(접선) 상황 → 교점 2개(할선) 상황으로 변경 (조건 위상)",
            "거리 = 반지름 → 판별식 D>0 경로 (풀이 경로)",
            "원·직선 계수 값 변경 (데이터)",
        ],
        rule_ids=rule_ids,
        construction_blueprint="원-직선 위치 관계를 접선에서 할선 상황으로 재구성",
    )
    plan_failures = validate_plan(plan)
    if plan_failures:
        print("[plan failures]", [f.model_dump() for f in plan_failures], file=sys.stderr)
        return 1

    # 4) 상황 변형 후보 생성 (할선 + 원 내부 걷기) + 계획 충실 검증
    variants = VariationEngine(scope).generate_variants(spec, plan)
    for candidate in variants:
        drift = validate_candidate_against_plan(candidate, plan, spec)
        if drift:
            print("[candidate failures]", [f.model_dump() for f in drift], file=sys.stderr)
            return 1

    # 5) 각 변형의 고정 검증
    verified = []
    for candidate in variants:
        new_baseline = solver.solve_text(candidate.problem_text)
        bare_spec = ProblemSpec(
            spec_id="verify",
            source_text=candidate.problem_text,
            curriculum_version="2022 개정",
            exam_scope=["도형의 방정식"],
            core_concepts=["원"],
            objective=MathStatement(id="goal", natural_language="문제 본문"),
            answer_type="expression",
            unresolved_assumptions=[],
        )
        new_gate = SourceGate().evaluate(bare_spec, new_baseline)
        rubric = Rubric(
            graph_id="graph-demo",
            items=[
                RubricItem(node_id=step.step_id, score=2, description=step.statement)
                for step in candidate.solution_steps
            ],
            total_points=2 * len(candidate.solution_steps),
            derived_from_verified=True,
        )
        verified.append((candidate, new_baseline, new_gate, rubric))

    # 6) 출력
    print("=" * 70)
    print("1. 원문 (시험지 광문고 2018 Q21)")
    print("-" * 70)
    print(raw_text)
    print()
    print("2. 원문 분석 (ProblemSpec)")
    print("-" * 70)
    print(f"  핵심 개념 : {spec.core_concepts}")
    print(f"  목표      : {spec.objective.natural_language}")
    print(f"  답 형태   : {spec.answer_type}")
    print()
    print("3. 원문 독립 풀이 + Source Gate")
    print("-" * 70)
    print(f"  게이트 상태 : {gate.status.value}  ({gate.reason})")
    print(f"  검증된 해    : {baseline.answer_set}")
    for check in baseline.verification_checks:
        print(f"    [{check.status}] {check.claim}  ({check.evidence})")
    print()
    print("4. 변형 계획")
    print("-" * 70)
    print(f"  보존 요소      : {plan.preserved_concepts}")
    print(f"  변경 차원      : {[d.value for d in plan.changed_dimensions]}")
    print(f"  적용 규칙      : {plan.rule_ids}")
    print(f"  구성 청사진    : {plan.construction_blueprint}")
    print()

    labels = [
        "5A. 변형 후보 1 — 접선(접점 1개) → 할선(두 점에서 만남)",
        "5B. 변형 후보 2 — 원 내부 걷기로 중심 구하기",
    ]
    for index, (candidate, new_baseline, new_gate, rubric) in enumerate(verified):
        label = labels[index]
        print(label)
        print("-" * 70)
        print(f"  [문제] {candidate.problem_text}")
        print(f"  [최종 답(주장)] {candidate.final_answer_claim}")
        print("  [단계별 해설]")
        for step in candidate.solution_steps:
            print(f"    {step.step_id}. {step.statement}")
        print(f"  [부분점수 루브릭] 총 {rubric.total_points}점")
        for item in rubric.items:
            print(f"    {item.node_id}: {item.score}점")
        print("  [변형 설명 (실제 변경 차원)]")
        for evidence in candidate.transformation_evidence:
            print(f"    - {evidence['dimension']}: {evidence['description']}")
        print("  [신규 문제 고정 검증]")
        print(f"    게이트 상태 : {new_gate.status.value}  ({new_gate.reason})")
        print(f"    검증된 해   : {new_baseline.answer_set}")
        for check in new_baseline.verification_checks:
            print(f"    [{check.status}] {check.claim}  ({check.evidence})")
        print()
    print("=" * 70)
    return 0


def parse_run_args(argv: list[str]) -> argparse.Namespace:
    """run 명령 인자 파서 (기본값: 광명북고 2023 Q19)."""
    parser = argparse.ArgumentParser(prog="math-variant run")
    parser.add_argument("source_path", nargs="?", default=_DEFAULT_SOURCE)
    parser.add_argument("question_number", nargs="?", default="19")
    return parser.parse_args(argv)


def resolve_source_question(source_path: Path, question_number: str) -> dict[str, Any] | None:
    """시험지 JSON 파일에서 문항 번호로 원문을 찾는다."""
    import json

    questions = json.loads(source_path.read_text(encoding="utf-8"))
    return next((q for q in questions if str(q["question_number"]) == question_number), None)


def run_pipeline(argv: list[str] | None = None) -> int:
    """LLM 다중 에이전트 파이프라인을 실행하고 결과를 출력한다."""
    args = parse_run_args(argv or [])
    source_path = Path(args.source_path)
    if not source_path.is_absolute():
        source_path = REPO_ROOT / source_path
    if not source_path.is_file():
        print(f"시험지 파일 없음: {source_path}", file=sys.stderr)
        return 1
    question = resolve_source_question(source_path, args.question_number)
    if question is None:
        print(f"문항 없음: {args.question_number}", file=sys.stderr)
        return 1

    from math_variant.agents.blind import LLMBlindSolver
    from math_variant.agents.code_reviewer import CodeReviewAgent
    from math_variant.agents.critic import CriticAgent
    from math_variant.agents.generator import GeneratorAgent
    from math_variant.agents.ideator import IdeatorAgent
    from math_variant.agents.judge import JudgeAgent
    from math_variant.agents.pipeline import AgentPipeline
    from math_variant.agents.planner import PlannerAgent
    from math_variant.agents.schemas import register_agent_schemas
    from math_variant.agents.selector import SelectorAgent
    from math_variant.agents.vision_artist import VisionArtist
    from math_variant.providers.factory import build_provider_registry
    from math_variant.providers.registry import SchemaRegistry
    from math_variant.providers.resolver import RoleResolver
    from math_variant.providers.settings import ProviderSettings
    from math_variant.providers.structured import StructuredOutputEngine
    from math_variant.sandbox.provider import DockerSandboxProvider
    from math_variant.services.blind_solver import BlindSolver
    from math_variant.services.normalize import normalize_source

    settings = ProviderSettings()
    registry = build_provider_registry(settings)
    schemas = SchemaRegistry()
    register_agent_schemas(schemas)
    resolver = RoleResolver(settings.role_policy(), registry)
    engine = StructuredOutputEngine(primary=None, fallback=None, schemas=schemas)
    engine.role_resolver = resolver

    def _prompt(name: str) -> str:
        return (PROMPTS_DIR / name).read_text(encoding="utf-8")

    figures_dir = Path("runs") / "figures"
    pipeline = AgentPipeline(
        planner=PlannerAgent(engine, _prompt("planner.md")),
        ideator=IdeatorAgent(engine, _prompt("ideator.md")),
        selector=SelectorAgent(engine, _prompt("selector.md")),
        generator=GeneratorAgent(engine, _prompt("candidate_generator.md")),
        code_reviewer=CodeReviewAgent(engine, _prompt("code_reviewer.md")),
        critic=CriticAgent(engine, _prompt("critic.md")),
        judge=JudgeAgent(engine, _prompt("judge.md")),
        vision=VisionArtist(engine, _prompt("vision.md"), figures_dir),
        sandbox=DockerSandboxProvider(image="math-variant-sandbox:test"),
        blind_solvers=BlindSolver(
            LLMBlindSolver(engine, _prompt("blind_solver.md"), "A"),
            LLMBlindSolver(engine, _prompt("blind_solver.md"), "B"),
            {"원문 정답": str(question.get("answer") or ""), "해설": ""},
        ),
        runs_dir=Path("runs"),
        ideator_count=3,
        max_refine=2,
    )

    report = pipeline.run(normalize_source(question["question_text"]))

    print("=" * 70)
    print(f"run_id: {report.run_id}")
    print(f"원문 문항 {args.question_number}: {question['question_text'][:80]}...")
    print("-" * 70)
    for i, entry in enumerate(report.ranking, start=1):
        candidate = next(
            (v for v in report.candidates if v.candidate.candidate_id == entry["candidate_id"]),
            None,
        )
        if candidate is None:
            continue
        print(f"[{i}] {candidate.candidate.candidate_id} (score {entry.get('score', '-')})")
        print(f"    상태: {candidate.status}")
        print(f"    문제: {candidate.candidate.problem_text}")
        print(f"    주장 답: {candidate.candidate.final_answer_claim}")
        if candidate.test_outcome:
            print(
                f"    샌드박스 검증: {candidate.test_outcome.verdict.value} "
                f"({candidate.test_outcome.detail[:80]})"
            )
        if candidate.blind_consensus:
            print(f"    블라인드 합의: {candidate.blind_consensus.status}")
        if candidate.critic:
            print(f"    비평 점수: {candidate.critic.score:.1f}")
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    command = args[0] if args else "gate"
    if command == "gate":
        return run_gates()
    if command == "check-locks":
        return check_locks()
    if command == "demo":
        return run_demo()
    if command == "run":
        return run_pipeline(args[1:])
    print(f"알 수 없는 명령: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover - 엔트리포인트
    raise SystemExit(main())

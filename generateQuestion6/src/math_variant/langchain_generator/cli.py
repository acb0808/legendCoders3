"""LangChain 문제 생성 CLI 진입점 (math-variant-lc).

사용법:
  # LangGraph 전체 파이프라인 — 기존 `math-variant run` 과 동일한 흐름·출력
  math-variant-lc run [시험지] [문항] [--difficulty 중상]

  # (레거시) 단일 패스 생성기 — planner→ideator→generator 후보 1건
  math-variant-lc [시험지] [문항] [--provider deepseek] [--model MODEL]
                 [--difficulty 중상] [--out runs/langchain_report.json]

기존 httpx 파이프라인과 병행하는 별도 진입점이다. `run` 서브커맨드는
LangGraph 기반 전체 파이프라인을 실행해 `runs/report.json`(PipelineReport)을
남기므로, 기존 파이프라인과 드롭인 교체가 가능하다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from math_variant.errors import MathVariantError
from math_variant.langchain_generator.generator import build_langchain_generator
from math_variant.langchain_generator.pipeline import build_langchain_pipeline
from math_variant.services.normalize import normalize_source

REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_SOURCE = "시험지/[2023년 기출] 광명북고1-2 중간 (주)_structured.json"


def parse_args(argv: list[str]) -> argparse.Namespace:
    """LangChain 생성 CLI 인자 파서 (단일 패스)."""
    parser = argparse.ArgumentParser(prog="math-variant-lc")
    parser.add_argument("source_path", nargs="?", default=_DEFAULT_SOURCE)
    parser.add_argument("question_number", nargs="?", default="19")
    parser.add_argument("--provider", default="deepseek")
    parser.add_argument("--model", default=None)
    parser.add_argument("--difficulty", default="")
    parser.add_argument("--out", default="runs/langchain_report.json")
    return parser.parse_args(argv)


def parse_run_args(argv: list[str]) -> argparse.Namespace:
    """run 서브커맨드 인자 파서 (기본값: 광명북고 2023 Q19)."""
    parser = argparse.ArgumentParser(prog="math-variant-lc run")
    parser.add_argument("source_path", nargs="?", default=_DEFAULT_SOURCE)
    parser.add_argument("question_number", nargs="?", default="19")
    parser.add_argument("--difficulty", default="")
    return parser.parse_args(argv)


def resolve_source_question(source_path: Path, question_number: str) -> dict[str, Any] | None:
    """시험지 JSON 파일에서 문항 번호로 원문을 찾는다."""
    questions = json.loads(source_path.read_text(encoding="utf-8"))
    return next((q for q in questions if str(q["question_number"]) == question_number), None)


def _resolve_source_path(source_path: Path) -> Path | None:
    if not source_path.is_absolute():
        source_path = REPO_ROOT / source_path
    if not source_path.is_file():
        print(f"시험지 파일 없음: {source_path}", file=sys.stderr)
        return None
    return source_path


def run_generate(argv: list[str]) -> int:
    """단일 패스 생성기 — 시험지 문항 하나를 변형해 후보 1건을 JSON 으로 저장한다."""
    args = parse_args(argv)
    source_path = _resolve_source_path(Path(args.source_path))
    if source_path is None:
        return 1
    question = resolve_source_question(source_path, args.question_number)
    if question is None:
        print(f"문항 없음: {args.question_number}", file=sys.stderr)
        return 1

    generator = build_langchain_generator(provider=args.provider, model=args.model)
    result = generator.generate(
        normalize_source(question["question_text"]),
        difficulty_target=args.difficulty,
    )
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"저장 완료: {out_path}")
    return 0


def run_pipeline(argv: list[str]) -> int:
    """LangGraph 전체 파이프라인 — 기존 `math-variant run` 과 동일하게 실행한다."""
    args = parse_run_args(argv)
    source_path = _resolve_source_path(Path(args.source_path))
    if source_path is None:
        return 1
    question = resolve_source_question(source_path, args.question_number)
    if question is None:
        print(f"문항 없음: {args.question_number}", file=sys.stderr)
        return 1

    pipeline = build_langchain_pipeline(
        ideator_count=3,
        max_refine=2,
        on_event=None,
        runs_dir=Path("runs"),
        figures_dir=Path("runs") / "figures",
        sandbox_image="math-variant-sandbox:test",
        forbidden_context={"원문 정답": str(question.get("answer") or ""), "해설": ""},
    )
    try:
        report = pipeline.run(
            normalize_source(question["question_text"]), difficulty_target=args.difficulty
        )
    except MathVariantError as exc:
        print(f"파이프라인 실행 실패: [{exc.code}] {exc.error.message}", file=sys.stderr)
        return 1

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
    """시험지 문항 하나를 LangChain 파이프라인으로 변형해 리포트를 저장한다."""
    args = sys.argv[1:] if argv is None else argv
    command = args[0] if args else ""
    if command == "run":
        return run_pipeline(args[1:])
    return run_generate(args)


if __name__ == "__main__":  # pragma: no cover - 엔트리포인트
    raise SystemExit(main())

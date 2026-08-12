"""T07 — CLI run 명령 테스트."""

from __future__ import annotations

from math_variant.cli import parse_run_args, resolve_source_question


def test_parse_run_args_defaults_to_gwangmyeongbukgo_q19() -> None:
    args = parse_run_args([])
    assert args.question_number == "19"
    assert "광명북고" in args.source_path


def test_parse_run_args_overrides() -> None:
    args = parse_run_args(["시험지/기타.json", "21"])
    assert args.question_number == "21"
    assert args.source_path == "시험지/기타.json"


def test_resolve_source_question_finds_19() -> None:
    from math_variant.cli import REPO_ROOT

    source = REPO_ROOT / "시험지" / "[2023년 기출] 광명북고1-2 중간 (주)_structured.json"
    question = resolve_source_question(source, "19")
    assert question is not None
    assert question["question_number"] == "19"
    assert "포물선" in question["question_text"]

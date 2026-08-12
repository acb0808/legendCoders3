"""T08 — 문제 라이브러리 저장소 테스트."""

from __future__ import annotations

from pathlib import Path

from math_variant.api.problems import ProblemStore
from math_variant.services.normalize import normalize_source


def _store(tmp_path: Path) -> ProblemStore:
    return ProblemStore(tmp_path)


def test_register_and_list(tmp_path: Path) -> None:
    store = _store(tmp_path)
    problem = store.register("포물선 y=x^2 의 접선을 구하시오.", title="T1")
    assert problem.source == "manual"
    listed = store.list()
    assert len(listed) == 1
    assert listed[0].problem_id == problem.problem_id


def test_register_is_idempotent_by_normalized_hash(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.register("포물선 y = x^2 의 접선", title="A")
    second = store.register("포물선 y = x^2 의 접선", title="B")
    assert first.problem_id == second.problem_id
    assert len(store.list()) == 1


def test_delete_removes_problem(tmp_path: Path) -> None:
    store = _store(tmp_path)
    problem = store.register("본문")
    store.delete(problem.problem_id)
    assert store.list() == []


def test_approved_returns_only_approved(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.register("원문제")
    approved = store.register("승인된 문제", source="approved", source_run_id="run-1")
    assert [p.problem_id for p in store.approved()] == [approved.problem_id]


def test_register_approved_stores_run_ref(tmp_path: Path) -> None:
    store = _store(tmp_path)
    problem = store.register("본문", source="approved", source_run_id="run-abc")
    assert problem.source_run_id == "run-abc"
    assert problem.text_hash == __import__("hashlib").sha256(
        normalize_source("본문").encode("utf-8")
    ).hexdigest()


def test_problem_not_found_raises(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        store.delete("missing")
    except ValueError:
        pass
    else:
        raise AssertionError("존재하지 않는 문제 삭제는 실패해야 한다")

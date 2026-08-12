"""T08 — 문제 라이브러리 저장소 테스트."""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

from math_variant.api.problems import ProblemStore
from math_variant.services.normalize import normalize_source


def _store(tmp_path: Path) -> ProblemStore:
    return ProblemStore(tmp_path)


def test_register_and_list(tmp_path: Path) -> None:
    store = _store(tmp_path)
    problem = store.register("포물선 y=x^2 의 접선을 구하시오.", title="T1")
    assert problem.source == "manual"
    listed = store.list_problems()
    assert len(listed) == 1
    assert listed[0].problem_id == problem.problem_id


def test_register_is_idempotent_by_normalized_hash(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.register("포물선 y = x^2 의 접선", title="A")
    second = store.register("포물선  y = x^2 의 접선", title="B")
    assert first.problem_id == second.problem_id
    assert len(store.list_problems()) == 1


def test_register_rejects_whitespace_only(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        store.register("   ")
    except ValueError:
        pass
    else:
        raise AssertionError("공백만 있는 문제 등록은 실패해야 한다")


def test_register_is_thread_safe(tmp_path: Path) -> None:
    store = _store(tmp_path)
    results: list[object] = []
    errors: list[Exception] = []

    def worker() -> None:
        try:
            results.append(store.register("동일한 문제 본문", title="동시"))
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len({r.problem_id for r in results if hasattr(r, "problem_id")}) == 1
    assert len(store.list_problems()) == 1


def test_delete_removes_problem(tmp_path: Path) -> None:
    store = _store(tmp_path)
    problem = store.register("본문")
    store.delete(problem.problem_id)
    assert store.list_problems() == []


def test_get_returns_registered_problem(tmp_path: Path) -> None:
    store = _store(tmp_path)
    problem = store.register("본문")
    assert store.get(problem.problem_id) == problem


def test_get_missing_raises(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        store.get("missing")
    except ValueError:
        pass
    else:
        raise AssertionError("존재하지 않는 문제 조회는 실패해야 한다")


def test_approved_returns_only_approved(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.register("원문제")
    approved = store.register("승인된 문제", source="approved", source_run_id="run-1")
    assert [p.problem_id for p in store.approved()] == [approved.problem_id]


def test_register_approved_stores_run_ref(tmp_path: Path) -> None:
    store = _store(tmp_path)
    problem = store.register("본문", source="approved", source_run_id="run-abc")
    assert problem.source_run_id == "run-abc"
    assert problem.text_hash == hashlib.sha256(
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

"""T08 — 생성 작업(Job) 저장소 테스트."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from math_variant.api.jobs import CreateOptions, JobStore
from math_variant.events import EventStage, PipelineEvent


def _store(tmp_path: Path) -> JobStore:
    return JobStore(tmp_path)


def test_create_save_load(tmp_path: Path) -> None:
    store = _store(tmp_path)
    job = store.create("원문", CreateOptions(difficulty_target="중상"))
    assert job.status == "queued"
    loaded = store.load(job.job_id)
    assert loaded.run_id == job.run_id
    assert loaded.options.difficulty_target == "중상"


def test_append_event_persists(tmp_path: Path) -> None:
    store = _store(tmp_path)
    job = store.create("원문", CreateOptions())
    event = PipelineEvent(
        event_id="e1",
        type="stage",
        stage=EventStage.PLANNER,
        status="started",
        message="기획 시작",
    )
    store.append_event(job.job_id, event)
    reloaded = store.load(job.job_id)
    assert len(reloaded.events) == 1
    assert reloaded.events[0].stage == EventStage.PLANNER


def test_set_status_and_error(tmp_path: Path) -> None:
    store = _store(tmp_path)
    job = store.create("원문", CreateOptions())
    store.set_status(job.job_id, "running")
    assert store.load(job.job_id).status == "running"
    store.fail(job.job_id, "boom", "AGENT_UNRESOLVED")
    failed = store.load(job.job_id)
    assert failed.status == "failed"
    assert failed.error == {"message": "boom", "code": "AGENT_UNRESOLVED"}


def test_complete_sets_report(tmp_path: Path) -> None:
    store = _store(tmp_path)
    job = store.create("원문", CreateOptions())
    store.complete(job.job_id, {"run_id": job.run_id, "candidates": 1})
    completed = store.load(job.job_id)
    assert completed.status == "completed"
    assert completed.report == {"run_id": job.run_id, "candidates": 1}


def test_list_sorted_by_created_desc(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.create("첫번째")
    time.sleep(0.002)
    second = store.create("두번째")
    jobs = store.list_jobs()
    assert len(jobs) == 2
    assert jobs[0].created_at >= jobs[1].created_at
    assert {j.job_id for j in jobs} == {first.job_id, second.job_id}


def test_load_missing_raises(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        store.load("missing")
    except ValueError:
        pass
    else:
        raise AssertionError("존재하지 않는 job 조회는 실패해야 한다")


def test_concurrent_append_events_are_not_lost(tmp_path: Path) -> None:
    store = _store(tmp_path)
    job = store.create("원문", CreateOptions())
    event = PipelineEvent(
        event_id="e",
        type="stage",
        stage=EventStage.PLANNER,
        status="done",
    )

    def worker() -> None:
        for _ in range(20):
            store.append_event(job.job_id, event)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(store.load(job.job_id).events) == 80

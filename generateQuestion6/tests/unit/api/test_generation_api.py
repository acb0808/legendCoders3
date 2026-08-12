"""T08 — 생성 작업 API 테스트 (fake 파이프라인 러너 사용)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from math_variant.api import app as api_module


class _FakeRunner:
    """실제 LLM 없이 즉시 이벤트를 방출하고 완료하는 러너."""

    def __init__(self) -> None:
        self.started: list[dict[str, Any]] = []

    def start(self, job_id: str, source_text: str, options: dict[str, Any]) -> None:
        self.started.append({"job_id": job_id, "source_text": source_text, "options": options})
        from math_variant.events import EventStage, PipelineEvent

        store = api_module._default_jobs()
        store.set_status(job_id, "running")
        store.append_event(
            job_id,
            PipelineEvent(
                event_id="e1", type="stage", stage=EventStage.PLANNER,
                status="done", message="기획 완료", ts=datetime.now(UTC),
            ),
        )
        store.append_event(
            job_id,
            PipelineEvent(
                event_id="e2", type="llm_call", stage=EventStage.PLANNER,
                status="done", ts=datetime.now(UTC),
                data={"role": "planner", "schema": "PlannerOutput", "provider": "fake",
                      "model": "m", "temperature": 0.2, "attempts": 1,
                      "latency_ms": 5, "cost_usd": 0.0, "ok": True,
                      "summary": {"core_concepts": ["포물선"]}, "error": None},
            ),
        )
        store.complete(job_id, {"run_id": job_id, "candidates": 1})


@pytest.fixture()
def client(tmp_path: Path, monkeypatch) -> TestClient:
    from math_variant.api.jobs import JobStore
    from math_variant.api.problems import ProblemStore
    from math_variant.api.storage import RunStore

    api_module._store = None
    api_module._jobs = None
    api_module._problems = None
    monkeypatch.setattr(api_module, "_store", RunStore(tmp_path / "runs"))
    monkeypatch.setattr(api_module, "_jobs", JobStore(tmp_path / "jobs"))
    monkeypatch.setattr(api_module, "_problems", ProblemStore(tmp_path / "problems"))
    monkeypatch.setattr(api_module, "_runner", _FakeRunner())
    api_module._reset_active_job()
    return TestClient(api_module.app)


def test_create_generation_returns_job(client: TestClient) -> None:
    response = client.post(
        "/api/generations",
        json={"source": {"mode": "text", "text": "포물선 y=x^2 의 접선"}, "options": {}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["run_id"] == body["job_id"]
    job = client.get(f"/api/generations/{body['job_id']}").json()
    assert job["status"] in {"running", "completed"}


def test_create_generation_requires_source_text(client: TestClient) -> None:
    response = client.post(
        "/api/generations",
        json={"source": {"mode": "text", "text": "   "}, "options": {}},
    )
    assert response.status_code == 422


def test_create_generation_concurrent_rejected(client: TestClient) -> None:
    client.post(
        "/api/generations",
        json={"source": {"mode": "text", "text": "첫번째"}, "options": {}},
    )
    api_module._active_job_id = "run-stale"
    response = client.post(
        "/api/generations",
        json={"source": {"mode": "text", "text": "두번째"}, "options": {}},
    )
    assert response.status_code == 409


def test_generation_events_sse(client: TestClient) -> None:
    created = client.post(
        "/api/generations",
        json={"source": {"mode": "text", "text": "원문"}, "options": {}},
    ).json()
    with client.stream("GET", f"/api/generations/{created['job_id']}/events") as stream:
        lines = "".join(stream.iter_text())
    assert "planner" in lines
    assert "llm_call" in lines


def test_generation_from_problem_source(client: TestClient) -> None:
    problem = client.post("/api/problems", json={"text": "원문제", "title": "T1"}).json()
    response = client.post(
        "/api/generations",
        json={"source": {"mode": "problem", "problem_id": problem["problem_id"]}, "options": {}},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_generation_missing_problem_404(client: TestClient) -> None:
    response = client.post(
        "/api/generations",
        json={"source": {"mode": "problem", "problem_id": "problem-nope"}, "options": {}},
    )
    assert response.status_code == 404

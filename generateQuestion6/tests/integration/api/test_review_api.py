"""T06.4 — API 계약·상태 테스트 (검증 후보 노출·승인/반려 게이트)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from math_variant.api.app import app
from math_variant.api.jobs import JobStore
from math_variant.api.problems import ProblemStore
from math_variant.api.storage import RunStore


@pytest.fixture()
def store(tmp_path: Path, monkeypatch) -> RunStore:
    from math_variant.api import app as app_module

    store = RunStore(tmp_path / "runs")
    monkeypatch.setattr(app_module, "_problems", ProblemStore(tmp_path / "problems"))
    monkeypatch.setattr(app_module, "_jobs", JobStore(tmp_path / "jobs"))
    store.save_run(
        "run-1",
        {
            "run_id": "run-1",
            "state": "TOOL_VERIFIED",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "candidates": [
                {
                    "candidate_id": "pass-full",
                    "plan_id": "plan-1",
                    "problem_text": "문제 본문",
                    "formalization": {"symbols": ["x"], "constraints": [], "goal": "접선"},
                    "final_answer_claim": "답",
                    "solution_steps": [{"step_id": "s1", "statement": "단계"}],
                    "transformation_evidence": [{"dimension": "representation"}],
                    "verification_status": "PASS",
                    "rubric": {"items": [{"score": 4}]},
                    "evidence": {"checks": [{"status": "PASS"}]},
                },
                {
                    "candidate_id": "unverified",
                    "plan_id": "plan-1",
                    "problem_text": "문제 본문",
                    "final_answer_claim": "답",
                    "solution_steps": [],
                    "transformation_evidence": [],
                    "verification_status": "UNVERIFIED",
                },
                {
                    "candidate_id": "pass-incomplete",
                    "plan_id": "plan-1",
                    "problem_text": "문제 본문",
                    "final_answer_claim": "",
                    "solution_steps": [],
                    "transformation_evidence": [],
                    "verification_status": "PASS",
                },
            ],
        },
    )
    return store


def _client(store: RunStore) -> TestClient:
    from math_variant.api import app as app_module

    app_module._store = store
    return TestClient(app)


def test_get_run_exposes_only_verified_complete_candidates(store: RunStore) -> None:
    client = _client(store)
    response = client.get("/api/runs/run-1")

    assert response.status_code == 200
    data = response.json()
    ids = [candidate["candidate_id"] for candidate in data["candidates"]]
    assert ids == ["pass-full"]
    assert "unverified" not in ids
    assert "pass-incomplete" not in ids


def test_reject_requires_reason(store: RunStore) -> None:
    client = _client(store)
    response = client.post(
        "/api/runs/run-1/candidates/pass-full/decision",
        json={"decision": "rejected", "reject_reason_code": None},
    )

    assert response.status_code == 422


def test_reject_with_reason_succeeds(store: RunStore) -> None:
    client = _client(store)
    response = client.post(
        "/api/runs/run-1/candidates/pass-full/decision",
        json={"decision": "rejected", "reject_reason_code": "MATH_ERROR"},
    )

    assert response.status_code == 201
    assert response.json()["decision"] == "rejected"
    assert response.json()["reject_reason_code"] == "MATH_ERROR"


def test_duplicate_approval_is_idempotent(store: RunStore) -> None:
    client = _client(store)
    first = client.post(
        "/api/runs/run-1/candidates/pass-full/decision",
        json={"decision": "approved", "reject_reason_code": None},
    )
    second = client.post(
        "/api/runs/run-1/candidates/pass-full/decision",
        json={"decision": "approved", "reject_reason_code": None},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["decided_at"] == second.json()["decided_at"]
    assert first.json()["decision"] == "approved"


def test_missing_run_returns_404(store: RunStore) -> None:
    client = _client(store)
    response = client.get("/api/runs/does-not-exist")
    assert response.status_code == 404


def test_list_runs_returns_summaries_sorted_by_update(store: RunStore) -> None:
    store.save_run(
        "run-2",
        {
            "run_id": "run-2",
            "state": "GENERATED",
            "created_at": "2026-01-02T00:00:00+00:00",
            "updated_at": "2026-01-02T00:00:00+00:00",
            "candidates": [
                {
                    "candidate_id": "other-pass",
                    "plan_id": "plan-2",
                    "problem_text": "문제 본문",
                    "final_answer_claim": "답",
                    "solution_steps": [{"step_id": "s1", "statement": "단계"}],
                    "transformation_evidence": [{"dimension": "representation"}],
                    "verification_status": "PASS",
                },
                {
                    "candidate_id": "other-unverified",
                    "plan_id": "plan-2",
                    "problem_text": "문제 본문",
                    "final_answer_claim": "답",
                    "verification_status": "UNVERIFIED",
                },
            ],
        },
    )
    client = _client(store)

    response = client.get("/api/runs")

    assert response.status_code == 200
    data = response.json()
    assert [run["run_id"] for run in data] == ["run-2", "run-1"]
    run_1 = next(run for run in data if run["run_id"] == "run-1")
    assert run_1["state"] == "TOOL_VERIFIED"
    assert run_1["candidate_count"] == 3
    assert run_1["verified_count"] == 2
    run_2 = next(run for run in data if run["run_id"] == "run-2")
    assert run_2["candidate_count"] == 2
    assert run_2["verified_count"] == 1


def test_list_runs_empty_returns_empty_array(tmp_path: Path) -> None:
    client = _client(RunStore(tmp_path / "runs"))
    response = client.get("/api/runs")
    assert response.status_code == 200
    assert response.json() == []


def test_cors_allows_web_origin_preflight(store: RunStore) -> None:
    client = _client(store)
    response = client.options(
        "/api/runs",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_blocks_unknown_origin(store: RunStore) -> None:
    client = _client(store)
    response = client.options(
        "/api/runs",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") is None

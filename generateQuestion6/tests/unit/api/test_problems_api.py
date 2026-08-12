"""T08 — 문제 라이브러리 API 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from math_variant.api import app as api_module
from math_variant.api.problems import ProblemStore


@pytest.fixture()
def client(tmp_path: Path, monkeypatch) -> TestClient:
    from math_variant.api.storage import RunStore

    api_module._store = None
    api_module._jobs = None
    api_module._problems = None
    monkeypatch.setattr(api_module, "_problems", ProblemStore(tmp_path / "problems"))
    monkeypatch.setattr(api_module, "_store", RunStore(tmp_path / "runs"))
    api_module._reset_active_job()
    return TestClient(api_module.app)


def test_register_and_list_problems(client: TestClient) -> None:
    created = client.post("/api/problems", json={"text": "포물선 y=x^2", "title": "T"}).json()
    assert created["source"] == "manual"
    listed = client.get("/api/problems").json()
    assert len(listed) == 1
    assert listed[0]["problem_id"] == created["problem_id"]


def test_register_duplicate_returns_same(client: TestClient) -> None:
    first = client.post("/api/problems", json={"text": "본문 A"}).json()
    second = client.post("/api/problems", json={"text": "본문 A"}).json()
    assert first["problem_id"] == second["problem_id"]


def test_delete_problem(client: TestClient) -> None:
    created = client.post("/api/problems", json={"text": "삭제할 문제"}).json()
    response = client.delete(f"/api/problems/{created['problem_id']}")
    assert response.status_code == 204
    assert client.get("/api/problems").json() == []


def test_approved_lists_approved_only(client: TestClient) -> None:
    client.post("/api/problems", json={"text": "직접 등록"})
    client.post(
        "/api/problems",
        json={"text": "승인 문제", "source": "approved", "source_run_id": "run-1"},
    )
    approved = client.get("/api/approved").json()
    assert len(approved) == 1
    assert approved[0]["source_run_id"] == "run-1"

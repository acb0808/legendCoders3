"""T00.1 — 프로젝트 골격과 CI 품질 게이트 테스트.

- T00.1-UT1: 실패하는 예제 테스트를 품질 게이트가 실패로 보고한다.
- T00.1-UT2: 통과 예제와 정의된 백엔드·프론트 품질 명령이 모두 0 코드로 종료된다.
- T00.1-UT3: Python 또는 Node 의존성 잠금 파일이 없으면 게이트가 실패한다.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from math_variant.tooling.quality import (
    BACKEND_GATES,
    FRONTEND_GATES,
    REQUIRED_LOCKFILES,
    check_dependency_locks,
    load_ci_workflow_commands,
)

RunPytest = Callable[[str], "subprocess.CompletedProcess[str]"]


def test_ut1_failing_example_is_reported_as_failure(isolated_pytest: RunPytest) -> None:
    """T00.1-UT1: 빈(실패) 예제 테스트는 0이 아닌 종료 코드로 보고된다."""
    result = isolated_pytest("def test_placeholder():\n    assert False\n")

    assert result.returncode != 0
    assert "1 failed" in result.stdout


def test_ut2_passing_example_exits_zero(isolated_pytest: RunPytest) -> None:
    """T00.1-UT2(a): 최소 구현이 있는 예제 테스트는 0 코드로 종료된다."""
    result = isolated_pytest("def test_placeholder():\n    assert 1 + 1 == 2\n")

    assert result.returncode == 0


def test_ut2_quality_commands_are_declared_for_both_stacks() -> None:
    """T00.1-UT2(b): 백엔드 lint·type·test와 프론트 lint·test 명령이 정의된다."""
    backend_ids = {gate.gate_id for gate in BACKEND_GATES}
    frontend_ids = {gate.gate_id for gate in FRONTEND_GATES}

    assert {"backend-lint", "backend-typecheck", "backend-test"} <= backend_ids
    assert {"frontend-lint", "frontend-test"} <= frontend_ids
    for gate in (*BACKEND_GATES, *FRONTEND_GATES):
        assert gate.command, f"{gate.gate_id} 명령이 비어 있다"
        assert gate.blocking is True


def test_ut2_ci_workflow_runs_every_declared_gate(repo_root: Path) -> None:
    """T00.1-UT2(c): CI가 선언된 모든 품질 명령을 병렬 잡으로 실행한다."""
    workflow = load_ci_workflow_commands(repo_root / ".github" / "workflows" / "ci.yml")

    for gate in BACKEND_GATES:
        assert gate.command in workflow["backend"], f"{gate.gate_id} 가 CI backend 잡에 없다"
    for gate in FRONTEND_GATES:
        assert gate.command in workflow["frontend"], f"{gate.gate_id} 가 CI frontend 잡에 없다"
    # 병렬 실행: 두 잡 사이에 needs 의존이 없어야 한다.
    assert workflow["parallel"] is True


def test_ut3_missing_lockfiles_fail_the_gate(tmp_path: Path) -> None:
    """T00.1-UT3(a): 잠금 파일이 없으면 구조화된 실패가 보고된다."""
    report = check_dependency_locks(tmp_path)

    assert report.ok is False
    assert {failure.path for failure in report.failures} == set(REQUIRED_LOCKFILES)
    assert all(failure.code == "DEPENDENCY_LOCK_MISSING" for failure in report.failures)


def test_ut3_repository_lockfiles_are_present(repo_root: Path) -> None:
    """T00.1-UT3(b): 실제 저장소에는 재현 가능한 잠금 파일이 존재한다."""
    report = check_dependency_locks(repo_root)

    assert report.ok is True, [failure.model_dump() for failure in report.failures]

"""공용 pytest 픽스처와 실행 정책.

전 테스트 계층(unit/property/contract/golden/integration/security)에서 공유하는
경로 픽스처와, 외부 자원(도커·실제 LLM 공급자)이 필요한 테스트의 skip 정책을 정의한다.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """저장소 루트 경로."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def testpaper_dir(repo_root: Path) -> Path:
    """원본 시험지 JSON 디렉터리."""
    return repo_root / "시험지"


@pytest.fixture
def isolated_pytest(tmp_path: Path) -> Iterator[object]:
    """임시 디렉터리에서 pytest 하위 프로세스를 실행하는 헬퍼.

    CI 품질 게이트가 실패를 실제로 보고하는지 검증할 때 사용한다.
    """

    def _run(test_source: str) -> subprocess.CompletedProcess[str]:
        (tmp_path / "test_example.py").write_text(test_source, encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "test_example.py"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

    yield _run


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """외부 자원이 없는 환경에서 docker·live_provider 테스트를 skip 처리한다."""
    docker_ok = _docker_available()
    live_ok = os.environ.get("MATH_VARIANT_LIVE_PROVIDER_TESTS") == "1"
    skip_docker = pytest.mark.skip(
        reason="docker 데몬을 사용할 수 없어 격리 샌드박스 테스트를 건너뜀"
    )
    skip_live = pytest.mark.skip(
        reason="MATH_VARIANT_LIVE_PROVIDER_TESTS=1 이 아니어서 실제 공급자 호출을 건너뜀"
    )
    for item in items:
        if "docker" in item.keywords and not docker_ok:
            item.add_marker(skip_docker)
        if "live_provider" in item.keywords and not live_ok:
            item.add_marker(skip_live)

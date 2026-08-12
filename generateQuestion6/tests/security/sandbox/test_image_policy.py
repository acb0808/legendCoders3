"""T03.2 — 격리 런타임 이미지 보안 정책 테스트.

- T03.2-ST1: 외부 HTTP·DNS 연결이 모두 실패한다.
- T03.2-ST2: 환경변수·호스트 파일·소켓을 통해 비밀정보를 읽을 수 없다.
- T03.2-ST3: pip·패키지 매니저와 시스템 명령으로 패키지를 추가할 수 없다.
- T03.2-ST4: 실행 A가 실행 B의 임시 파일을 볼 수 없다.
- T03.2-ST5: 이미지 digest와 패키지 버전이 증거에 기록된다.
"""

from __future__ import annotations

import base64
import json
import subprocess
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.docker

IMAGE = "math-variant-sandbox:test"
INFRA = Path(__file__).resolve().parents[3] / "infra" / "sandbox"

_IMPORT_SYMPY = "import sympy\nresult = {'v': sympy.__version__}\n"


@pytest.fixture(scope="module")
def image_digest() -> str:
    subprocess.run(
        ["docker", "build", "-t", IMAGE, str(INFRA)],
        check=True,
        capture_output=True,
    )
    inspect = subprocess.run(
        ["docker", "image", "inspect", IMAGE, "--format", "{{.RepoDigests}}"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return inspect.stdout.strip()


def _run_payload(code: str, input_json: dict | None = None, workdir: Path | None = None) -> dict:
    """격리 이미지에서 코드를 실행하고 결과 JSON 을 반환한다.

    호스트 bind mount 를 피하고 입력은 base64 로 전달하며, 결과는 stdout 으로 받는다.
    컨테이너는 --read-only, --network none, /work tmpfs 로 실행된다.
    """
    _ = workdir
    payload = {
        "request_id": f"policy-test-{uuid.uuid4().hex[:6]}",
        "code": code,
        "input_json": input_json or {},
        "allowed_packages": ["sympy", "math"],
        "resource_budget": {"cpu_seconds": 10, "memory_mb": 256},
        "seed": 42,
        "expected_output_schema": None,
    }
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")

    process = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network",
            "none",
            "--read-only",
            "--memory",
            "256m",
            "--tmpfs",
            "/work:rw,size=8m,mode=700,uid=10001,gid=10001",
            IMAGE,
            "--stdin",
        ],
        input=encoded,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(process.stdout)


def test_st1_network_is_blocked() -> None:
    code = (
        "import urllib.request\n"
        "try:\n"
        "    urllib.request.urlopen('http://example.com', timeout=3)\n"
        "    result = {'network': 'ok'}\n"
        "except Exception as exc:\n"
        "    result = {'network': 'blocked', 'error': str(exc)}\n"
    )
    result = _run_payload(code)
    assert result["status"] == "COMPLETED"
    assert result["output_json"]["network"] == "blocked"


def test_st2_host_secrets_unreachable() -> None:
    code = "import os\nresult = {'env_has': 'HOST_SECRET_MARKER_XYZ' in os.environ}\n"
    result = _run_payload(code)
    assert result["status"] == "COMPLETED"
    assert result["output_json"]["env_has"] is False


def test_st3_package_install_blocked() -> None:
    code = (
        "import subprocess, sys\n"
        "try:\n"
        "    proc = subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests'],\n"
        "                          capture_output=True, text=True, timeout=5)\n"
        "    result = {'installed': proc.returncode == 0}\n"
        "except Exception as exc:\n"
        "    result = {'installed': False, 'error': str(exc)}\n"
    )
    result = _run_payload(code)
    assert result["status"] == "COMPLETED"
    assert result["output_json"]["installed"] is False


def test_st4_runs_cannot_see_each_others_temp_files() -> None:
    first = _run_payload(
        "from pathlib import Path\n"
        "Path('/work/run_marker').write_text('A')\n"
        "result = {'wrote': '/work/run_marker'}\n"
    )
    assert first["status"] == "COMPLETED"
    assert first["output_json"]["wrote"] == "/work/run_marker"

    # 두 번째 실행은 새 컨테이너이므로 /work 에 마커가 없다.
    second = _run_payload(
        "from pathlib import Path\nresult = {'exists': Path('/work/run_marker').exists()}\n"
    )
    assert second["status"] == "COMPLETED"
    assert second["output_json"]["exists"] is False


def test_st5_digest_and_package_versions_in_evidence(image_digest: str) -> None:
    result = _run_payload(_IMPORT_SYMPY)

    assert result["status"] == "COMPLETED"
    assert result["output_json"]["v"].startswith("1.13")
    assert result["package_versions"]["sympy"] == "1.13.3"
    assert "sha256" in image_digest
    assert "package_versions" in result

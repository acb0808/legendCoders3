"""샌드박스 공급자 인터페이스와 로컬·도커 구현 (T03.1)."""

from __future__ import annotations

import subprocess
import time
from typing import Protocol, runtime_checkable

from math_variant.sandbox.contracts import (
    SandboxRequest,
    SandboxResult,
    SandboxStatus,
)


@runtime_checkable
class SandboxProvider(Protocol):
    """교체 가능한 샌드박스 실행 공급자."""

    name: str

    def execute(self, request: SandboxRequest) -> SandboxResult: ...


class LocalSandboxProvider:
    """로컬 개발용 공급자 — 신뢰 경계가 아닌 가벼운 대안.

    정책 위반(비밀·호스트 패턴)은 요청 검증에서 이미 차단되고, 여기서는
    실행 시간 초과와 코드 오류만 구분한다. 운영 환경에서는 DockerSandboxProvider 를 사용한다.
    """

    def __init__(self, timeout_seconds: float = 10.0, python_executable: str = "python") -> None:
        self.name = "local"
        self.timeout_seconds = timeout_seconds
        self.python_executable = python_executable

    def execute(self, request: SandboxRequest) -> SandboxResult:
        started = time.monotonic()
        import json

        embedded = json.dumps(request.input_json)
        script = (
            "import json, sys\n"
            f"data = json.loads({embedded!r})\n"
            f"result = eval({request.code!r}, {{}}, data)\n"
            "print(json.dumps(result))\n"
        )
        try:
            # 로컬 개발용 폴백으로 의도된 서브프로세스 실행.
            # 운영 경계는 DockerSandboxProvider(격리 이미지)가 담당한다.
            process = subprocess.run(
                [self.python_executable, "-c", script],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxResult(
                result_id=f"local-{request.request_id}",
                request_id=request.request_id,
                status=SandboxStatus.TIMEOUT,
                duration_ms=int((time.monotonic() - started) * 1000),
                provider_name=self.name,
                stderr=str(exc),
            )
        duration = int((time.monotonic() - started) * 1000)
        if process.returncode != 0:
            return SandboxResult(
                result_id=f"local-{request.request_id}",
                request_id=request.request_id,
                status=SandboxStatus.CODE_ERROR,
                stdout=process.stdout,
                stderr=process.stderr,
                duration_ms=duration,
                provider_name=self.name,
            )
        try:
            output = __import__("json").loads(process.stdout.strip() or "null")
        except (ValueError, TypeError):
            output = None
        return SandboxResult(
            result_id=f"local-{request.request_id}",
            request_id=request.request_id,
            status=SandboxStatus.COMPLETED,
            output_json=output if isinstance(output, dict) else None,
            stdout=process.stdout,
            stderr=process.stderr,
            duration_ms=duration,
            provider_name=self.name,
        )


class DockerSandboxProvider:
    """운영 공급자 — 격리 런타임 이미지에서 코드를 실행한다 (T03.2).

    컨테이너 경계: --network none, --read-only, --memory 제한, /work tmpfs,
    비특권 사용자(uid 10001). 입력은 base64 로 stdin 으로 전달하고 결과는 stdout 으로 받는다.
    """

    def __init__(self, image: str, memory_mb: int = 256, timeout_seconds: float = 30.0) -> None:
        self.name = "docker"
        self.image = image
        self.memory_mb = memory_mb
        self.timeout_seconds = timeout_seconds

    def execute(self, request: SandboxRequest) -> SandboxResult:
        import base64
        import json

        payload = {
            "request_id": request.request_id,
            "code": request.code,
            "input_json": request.input_json,
            "allowed_packages": request.allowed_packages,
            "resource_budget": request.resource_budget.model_dump(),
            "seed": request.seed,
            "expected_output_schema": request.expected_output_schema,
        }
        encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
        command = [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network",
            "none",
            "--read-only",
            "--memory",
            f"{self.memory_mb}m",
            "--tmpfs",
            "/work:rw,size=8m,mode=700,uid=10001,gid=10001",
            self.image,
            "--stdin",
        ]
        try:
            process = subprocess.run(
                command,
                input=encoded,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"샌드박스 컨테이너 시간 초과: {exc}") from exc

        if process.returncode != 0:
            raise RuntimeError(
                f"샌드박스 컨테이너 오류(exit {process.returncode}): {process.stderr[:300]}"
            )
        result_data = json.loads(process.stdout)
        result = SandboxResult.model_validate(result_data)
        # 재현 가능한 이미지 digest 를 증거에 기록한다 (T03.2-ST5).
        digest = self._image_digest()
        if digest:
            result = result.model_copy(update={"image_digest": digest})
        return result

    _digest_cache: str | None = None

    def _image_digest(self) -> str | None:
        if self._digest_cache:
            return self._digest_cache
        try:
            # 고정된 도커 CLI 호출 (격리 경계 운영 계약)
            process = subprocess.run(
                ["docker", "image", "inspect", self.image, "--format", "{{index .RepoDigests 0}}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
                check=False,
            )
        except subprocess.SubprocessError:
            return None
        digest = process.stdout.strip() if process.returncode == 0 else ""
        if digest:
            self._digest_cache = digest
        return digest or None

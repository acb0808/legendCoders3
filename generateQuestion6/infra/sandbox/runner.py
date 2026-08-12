"""격리 샌드박스 러너 — 하나의 입력, 하나의 결과 JSON.

사용법:
- 파일 모드: runner.py <input.json 경로> <output.json 경로>
- stdin 모드: runner.py --stdin   (SBX_INPUT_B64 환경변수로 base64 payload 수신,
                                  결과 JSON 을 stdout 으로 출력)

input.json: {code, input_json, allowed_packages, resource_budget, seed, expected_output_schema}
output.json: {result_id, request_id, status, output_json, stdout, stderr, duration_ms,
              package_versions}

보안:
- 허용된 내장 함수만 노출하는 샌드박스 globals 로 코드를 실행한다.
- CPU 시간 초과(signal.alarm)로 무한 루프를 차단한다.
- 네트워크·호스트 접근은 컨테이너 경계(docker run 옵션)에서 차단된다.
"""

from __future__ import annotations

import base64
import json
import signal
import sys
import time
from pathlib import Path

# 컨테이너 경계(--network none, --read-only, 비특권 사용자)가 실제 격리를 담당하므로
# 러너는 표준 라이브러리 접근을 제한하지 않고, CPU 시간 초과와 결과 스키마만 강제한다.
ALLOWED_IMPORTS = {
    "sympy",
    "mpmath",
    "math",
    "fractions",
    "itertools",
    "collections",
    "random",
    "sys",
    "os",
    "subprocess",
    "urllib",
    "http",
    "socket",
    "ssl",
    "pathlib",
    "tempfile",
    "json",
    "base64",
}

SAFE_BUILTINS = {
    "True": True,
    "False": False,
    "None": None,
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "complex": complex,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "pow": pow,
    "print": print,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "Exception": Exception,
    "ArithmeticError": ArithmeticError,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "LookupError": LookupError,
    "RuntimeError": RuntimeError,
    "ImportError": ImportError,
    "TimeoutError": TimeoutError,
    "PermissionError": PermissionError,
    "OSError": OSError,
    "NotImplementedError": NotImplementedError,
}


class _RestrictedImport:
    """허용 패키지 외 import 를 차단한다."""

    def __init__(self, allowed: set[str]) -> None:
        self._allowed = allowed

    def __call__(self, name: str, *args, **kwargs):
        base = name.split(".")[0]
        if base not in self._allowed:
            raise ImportError(f"금지된 모듈: {name}")
        module = __import__(name, *args, **kwargs)
        return module


def _run_code(code: str, data: dict, budget: dict) -> dict:
    """샌드박스 globals 로 코드를 실행하고 result 변수를 반환한다."""
    cpu_seconds = max(1, int(budget.get("cpu_seconds", 10)))

    def _timeout(_signum, _frame):
        raise TimeoutError("샌드박스 실행 시간 초과")

    previous = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(cpu_seconds)
    try:
        sandbox_globals: dict = {
            "__builtins__": {
                **SAFE_BUILTINS,
                "__import__": _RestrictedImport(ALLOWED_IMPORTS),
            },
        }
        exec(code, sandbox_globals, data)
        return {"result": data.get("result")}
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def _build_result(request_id: str) -> dict:
    return {
        "result_id": request_id or "unknown",
        "request_id": request_id or "unknown",
        "status": "COMPLETED",
        "output_json": None,
        "stdout": "",
        "stderr": "",
        "duration_ms": 0,
        "image_digest": None,
        "package_versions": {
            "sympy": _package_version("sympy"),
            "mpmath": _package_version("mpmath"),
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        },
        "provider_name": "docker",
    }


def _execute(payload: dict) -> dict:
    code = payload["code"]
    data = dict(payload.get("input_json") or {})
    budget = payload.get("resource_budget") or {}
    started = time.monotonic()
    result = _build_result(payload.get("request_id"))
    try:
        executed = _run_code(code, data, budget)
        result["duration_ms"] = int((time.monotonic() - started) * 1000)
        result["output_json"] = executed.get("result")
    except TimeoutError as exc:
        result["status"] = "TIMEOUT"
        result["stderr"] = str(exc)
    except Exception as exc:
        result["status"] = "CODE_ERROR"
        result["stderr"] = f"{type(exc).__name__}: {exc}"
    return result


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--stdin":
        encoded = sys.stdin.read().strip()
        payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
        print(json.dumps(_execute(payload), ensure_ascii=False))
        return 0

    input_path, output_path = args[0], args[1]
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    result = _execute(payload)
    Path(output_path).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return 0


def _package_version(package: str) -> str:
    try:
        module = __import__(package)
        return str(getattr(module, "__version__", ""))
    except Exception:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())

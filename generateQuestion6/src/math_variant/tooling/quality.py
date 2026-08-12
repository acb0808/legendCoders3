"""품질 게이트 정의 (T00.1).

백엔드·프론트엔드 품질 명령을 코드에서 단일 출처로 선언하고, CI 워크플로가 실제로 그
명령들을 병렬 잡으로 실행하는지 검증할 수 있게 한다. 의존성 잠금 파일 존재 여부도
구조화된 실패로 보고한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from math_variant.errors import ErrorCode, StructuredError

__all__ = [
    "BACKEND_GATES",
    "FRONTEND_GATES",
    "REQUIRED_LOCKFILES",
    "LockReport",
    "QualityGate",
    "check_dependency_locks",
    "load_ci_workflow_commands",
]


class QualityGate(BaseModel):
    """하나의 자동 품질 검사."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    gate_id: str
    description: str
    command: str
    working_directory: str = "."
    blocking: bool = True


BACKEND_GATES: tuple[QualityGate, ...] = (
    QualityGate(
        gate_id="backend-lint",
        description="ruff 정적 lint (보안·타입주석 규칙 포함)",
        command="ruff check src tests infra",
    ),
    QualityGate(
        gate_id="backend-format",
        description="ruff 포맷 검사",
        command="ruff format --check src tests infra",
    ),
    QualityGate(
        gate_id="backend-typecheck",
        description="mypy strict 타입 검사",
        command="mypy",
    ),
    QualityGate(
        gate_id="backend-test",
        description="pytest 백엔드 단위·계약·골드·통합 테스트",
        command="pytest",
    ),
)

FRONTEND_GATES: tuple[QualityGate, ...] = (
    QualityGate(
        gate_id="frontend-lint",
        description="Next.js ESLint 검사",
        command="npm run lint",
        working_directory="web",
    ),
    QualityGate(
        gate_id="frontend-typecheck",
        description="TypeScript 타입 검사",
        command="npm run typecheck",
        working_directory="web",
    ),
    QualityGate(
        gate_id="frontend-test",
        description="Vitest 컴포넌트·통합 테스트",
        command="npm run test",
        working_directory="web",
    ),
)

REQUIRED_LOCKFILES: tuple[str, ...] = (
    "requirements.lock.txt",
    "web/package-lock.json",
)


class LockReport(BaseModel):
    """의존성 잠금 검사 결과."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    failures: tuple[LockFailure, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.failures


class LockFailure(BaseModel):
    """누락되거나 빈 잠금 파일 하나에 대한 구조화된 실패."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: ErrorCode
    path: str
    message: str

    def as_error(self) -> StructuredError:
        return StructuredError(code=self.code, message=self.message, context={"path": self.path})


LockReport.model_rebuild()


def check_dependency_locks(root: Path) -> LockReport:
    """Python·Node 의존성 잠금 파일이 재현 가능하게 존재하는지 검사한다."""
    failures: list[LockFailure] = []
    for relative in REQUIRED_LOCKFILES:
        path = root / relative
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(
                LockFailure(
                    code=ErrorCode.DEPENDENCY_LOCK_MISSING,
                    path=relative,
                    message=(
                        "의존성 잠금 파일이 없거나 비어 있어 재현 가능한 설치를 보장할 수 없다: "
                        f"{relative}"
                    ),
                )
            )
    return LockReport(failures=tuple(failures))


def load_ci_workflow_commands(workflow_path: Path) -> dict[str, Any]:
    """CI 워크플로에서 잡별 run 명령과 병렬성 정보를 추출한다."""
    document = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    jobs: dict[str, Any] = document["jobs"]

    def commands(job_name: str) -> list[str]:
        steps = jobs[job_name].get("steps", [])
        return [str(step["run"]).strip() for step in steps if "run" in step]

    backend_needs = jobs["backend"].get("needs") or []
    frontend_needs = jobs["frontend"].get("needs") or []
    parallel = "frontend" not in backend_needs and "backend" not in frontend_needs

    return {
        "backend": commands("backend"),
        "frontend": commands("frontend"),
        "parallel": parallel,
        "jobs": sorted(jobs),
    }

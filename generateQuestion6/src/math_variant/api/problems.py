"""문제 라이브러리 저장소 (T08).

- 직접 등록(source="manual")과 승인 문제 자동 등록(source="approved")을 모두 저장한다.
- 중복 방지: 정규화 텍스트의 sha256 해시로 판정해 멱등으로 동작한다.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from builtins import list as builtin_list
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from math_variant.services.normalize import normalize_source


class Problem(BaseModel):
    """라이브러리 문제 하나."""

    model_config = ConfigDict(extra="forbid")

    problem_id: str
    title: str = ""
    text: str = Field(min_length=1)
    source: Literal["manual", "approved"] = "manual"
    source_run_id: str | None = None
    text_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProblemStore:
    """data/problems/*.json 형식의 문제 라이브러리."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, problem_id: str) -> Path:
        return self.base_dir / f"{problem_id}.json"

    def list(self) -> builtin_list[Problem]:
        problems: builtin_list[Problem] = []
        for path in sorted(self.base_dir.glob("*.json")):
            problems.append(Problem.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        problems.sort(key=lambda p: p.created_at.isoformat(), reverse=True)
        return problems

    def approved(self) -> builtin_list[Problem]:
        return [p for p in self.list() if p.source == "approved"]

    def get(self, problem_id: str) -> Problem:
        path = self._path(problem_id)
        if not path.is_file():
            raise ValueError(f"문제 없음: {problem_id}")
        return Problem.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def register(
        self,
        text: str,
        title: str = "",
        source: Literal["manual", "approved"] = "manual",
        source_run_id: str | None = None,
    ) -> Problem:
        """문제를 등록한다. 정규화 텍스트 해시로 중복이면 기존 문제를 반환한다."""
        text_hash = hashlib.sha256(normalize_source(text).encode("utf-8")).hexdigest()
        existing = next((p for p in self.list() if p.text_hash == text_hash), None)
        if existing is not None:
            return existing
        problem = Problem(
            problem_id=f"problem-{uuid.uuid4().hex[:8]}",
            title=title,
            text=text,
            source=source,
            source_run_id=source_run_id,
            text_hash=text_hash,
        )
        self._path(problem.problem_id).write_text(
            json.dumps(problem.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return problem

    def delete(self, problem_id: str) -> None:
        path = self._path(problem_id)
        if not path.is_file():
            raise ValueError(f"문제 없음: {problem_id}")
        path.unlink()

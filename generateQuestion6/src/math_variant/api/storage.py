"""API 스토리지 계층 (T06.4)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from math_variant.domain.candidate import CandidateProblem
from math_variant.domain.validation import ValidationEvidence

# 검토 화면에 노출할 후보가 갖춰야 하는 필수 산출물·증거 (T06.4-UT2)
REQUIRED_ARTIFACT_FIELDS = (
    "problem_text",
    "final_answer_claim",
    "solution_steps",
    "transformation_evidence",
)


class RunNotFoundError(ValueError):
    pass


class CandidateNotFoundError(ValueError):
    pass


def has_required_artifacts(
    candidate: CandidateProblem, evidence: ValidationEvidence | None
) -> bool:
    """후보가 필수 산출물과 검증 증거를 모두 갖췄는지 판정한다."""
    for field in REQUIRED_ARTIFACT_FIELDS:
        if not getattr(candidate, field):
            return False
    return bool(evidence and evidence.checks)


class RunStore:
    """GenerationRun 과 후보·증거를 JSON 파일로 저장한다 (MVP)."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _run_path(self, run_id: str) -> Path:
        return self.base_dir / f"{run_id}.json"

    def list_runs(self) -> list[dict[str, Any]]:
        """생성 실행 요약 목록 (업데이트 최신순)."""
        summaries: list[dict[str, Any]] = []
        for path in self.base_dir.glob("*.json"):
            data = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
            candidates = data.get("candidates", [])
            summaries.append(
                {
                    "run_id": data.get("run_id", path.stem),
                    "state": data.get("state", "UNKNOWN"),
                    "candidate_count": len(candidates),
                    "verified_count": sum(
                        1
                        for candidate in candidates
                        if candidate.get("verification_status") == "PASS"
                    ),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                }
            )
        summaries.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
        return summaries

    def load_run(self, run_id: str) -> dict[str, Any]:
        path = self._run_path(run_id)
        if not path.is_file():
            raise RunNotFoundError(run_id)
        return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))

    def save_run(self, run_id: str, data: dict[str, Any]) -> None:
        path = self._run_path(run_id)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def public_run(self, run_id: str) -> dict[str, Any]:
        """검토 화면용: 검증(PASS) 후보와 필수 산출물을 갖춘 후보만 노출한다."""
        data = self.load_run(run_id)
        candidates = data.get("candidates", [])
        visible = [
            candidate
            for candidate in candidates
            if candidate.get("verification_status") == "PASS" and _has_artifacts(candidate)
        ]
        return {
            "run_id": data.get("run_id", run_id),
            "state": data.get("state", "UNKNOWN"),
            "candidates": visible,
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }

    def apply_decision(
        self,
        run_id: str,
        candidate_id: str,
        decision: str,
        reject_reason_code: str | None,
    ) -> dict[str, Any]:
        """후보 결정을 저장한다. 이미 결정된 후보는 중복 이벤트를 만들지 않는다."""
        data = self.load_run(run_id)
        for candidate in data.get("candidates", []):
            if candidate.get("candidate_id") != candidate_id:
                continue
            existing = candidate.get("human_decision")
            if existing is not None:
                return cast(dict[str, Any], existing)
            event = {
                "run_id": run_id,
                "candidate_id": candidate_id,
                "decision": decision,
                "reject_reason_code": reject_reason_code if decision == "rejected" else None,
                "decided_at": datetime.now(UTC).isoformat(),
            }
            candidate["human_decision"] = event
            self.save_run(run_id, data)
            return event
        raise CandidateNotFoundError(candidate_id)


def _has_artifacts(candidate: dict[str, Any]) -> bool:
    required = (*REQUIRED_ARTIFACT_FIELDS, "rubric", "evidence")
    for field in required:
        if not candidate.get(field):
            return False
    return True

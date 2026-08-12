"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { listRuns } from "@/lib/api";
import type { RunSummary } from "@/lib/types";

/** 실행 목록 — 각 실행의 검토 화면(/runs/<runId>/review)으로 이동한다. */
export function RunList() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listRuns()
      .then((data) => {
        if (!cancelled) {
          setRuns(data);
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : String(reason));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <p className="runs-error">실행 목록을 불러오지 못했습니다: {error}</p>;
  }
  if (runs === null) {
    return <p className="runs-loading">불러오는 중…</p>;
  }
  if (runs.length === 0) {
    return <p className="runs-empty">아직 생성된 실행이 없습니다.</p>;
  }

  return (
    <ul className="run-list" data-testid="run-list">
      {runs.map((run) => (
        <li key={run.run_id} className="run-row" data-testid={`run-row-${run.run_id}`}>
          <Link href={`/runs/${run.run_id}/review`}>
            <strong>{run.run_id}</strong>
          </Link>
          <span className="run-state">{run.state}</span>
          <span className="run-count">
            검증 후보 {run.verified_count} / 전체 {run.candidate_count}
          </span>
        </li>
      ))}
    </ul>
  );
}

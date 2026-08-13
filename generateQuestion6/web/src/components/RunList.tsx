"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { listRuns } from "@/lib/api";
import type { RunSummary } from "@/lib/types";

function sourceLabel(run: RunSummary): string {
  if (run.source?.label) {
    return run.source.label;
  }
  const text = (run.source?.text ?? "").replace(/<eq>|<\/eq>|\s+/g, " ").trim();
  if (text) {
    return text.length > 48 ? `${text.slice(0, 48)}…` : text;
  }
  return run.run_id;
}

function formatTime(ts: string | null): string {
  if (!ts) {
    return "";
  }
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/** 실행 목록 — 어떤 문제를 언제 실행했는지 최신순으로 보여주고 검토 화면으로 이동한다. */
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
            <strong>{sourceLabel(run)}</strong>
          </Link>
          <span className="run-time">{formatTime(run.created_at)}</span>
          <span className="run-state">{run.state}</span>
          <span className="run-count">
            검증 후보 {run.verified_count} / 전체 {run.candidate_count}
          </span>
        </li>
      ))}
    </ul>
  );
}

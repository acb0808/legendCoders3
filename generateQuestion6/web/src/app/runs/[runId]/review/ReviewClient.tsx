"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";

import { CandidateList } from "@/components/CandidateList";
import { getRun, postDecision } from "@/lib/api";
import type { Decision, GenerationRun } from "@/lib/types";

/** 검토 화면 클라이언트 — 실행 데이터를 불러오고 후보별 결정을 전송한다. */
export function ReviewClient({ runIdPromise }: { runIdPromise: Promise<{ runId: string }> }) {
  const { runId } = use(runIdPromise);
  const [run, setRun] = useState<GenerationRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getRun(runId)
      .then((data) => {
        if (!cancelled) {
          setRun(data);
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
  }, [runId]);

  if (error) {
    return <p className="review-error">{error}</p>;
  }
  if (run === null) {
    return <p className="review-loading">불러오는 중…</p>;
  }

  const handleDecide = async (candidateId: string, decision: Decision, reason: string | null) => {
    const event = await postDecision(runId, candidateId, decision, reason);
    setRun((current) => (current ? { ...current, ...event } : current));
  };

  return (
    <>
      <header className="review-header">
        <p className="review-eyebrow">
          <Link className="review-back" href="/">
            ← 실행 목록
          </Link>
        </p>
        <div className="review-title-row">
          <h1>후보 비교·검토</h1>
          <span className={`run-state-chip run-state-chip-${run.state}`}>{run.state}</span>
        </div>
        <p className="review-sub">
          실행 <code>{run.run_id}</code> · 검증을 통과한 후보만 노출
        </p>
      </header>
      <CandidateList
        candidates={run.candidates}
        onDecide={handleDecide}
      />
    </>
  );
}

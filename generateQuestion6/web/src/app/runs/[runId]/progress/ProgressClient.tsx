"use client";

import { use } from "react";
import Link from "next/link";

import { ProgressView } from "@/components/ProgressView";

/** 진행 화면 클라이언트 — 동적 경로 파라미터를 해석해 ProgressView 에 전달한다. */
export function ProgressClient({ runIdPromise }: { runIdPromise: Promise<{ runId: string }> }) {
  const { runId } = use(runIdPromise);
  return (
    <>
      <header className="progress-header">
        <p className="progress-eyebrow">
          <Link className="progress-back" href="/">
            ← 실행 목록
          </Link>
        </p>
        <h1>생성 진행</h1>
        <p className="progress-sub">
          실행 <code>{runId}</code> · 실시간 진행 상황
        </p>
      </header>
      <ProgressView jobId={runId} />
    </>
  );
}

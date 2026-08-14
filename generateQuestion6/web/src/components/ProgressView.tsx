"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { getJob, streamJobEvents } from "@/lib/api";
import type { JobEvent, JobStatus } from "@/lib/types";
import { CallLog } from "./CallLog";

const STAGE_ORDER = [
  "planner",
  "reference",
  "ideation",
  "selection",
  "generation",
  "code_review",
  "sandbox",
  "blind",
  "critic",
  "skill_mapping",
  "style_align",
  "judge",
  "done",
];

const STAGE_LABELS: Record<string, string> = {
  planner: "기획",
  reference: "참조 검색",
  ideation: "발상",
  selection: "선별",
  generation: "생성",
  code_review: "코드 심사",
  sandbox: "샌드박스 검증",
  blind: "블라인드 합의",
  critic: "비평",
  skill_mapping: "스킬 매핑",
  style_align: "스타일 정렬",
  judge: "집계",
  done: "완료",
};


/** 실시간 생성 진행 화면 — 단계 체크리스트 + LLM 호출 로그 (SSE). */
export function ProgressView({ jobId }: { jobId: string }) {
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [status, setStatus] = useState<JobStatus>("queued");
  const [error, setError] = useState<string | null>(null);
  const [reconnectKey, setReconnectKey] = useState(0);
  const logRef = useRef<HTMLDivElement>(null);
  const seenIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    getJob(jobId)
      .then((data) => {
        if (!cancelled) {
          setStatus(data.status);
          setEvents(data.events);
          seenIdsRef.current = new Set(data.events.map((event) => event.event_id));
          if (data.error?.message) {
            setError(data.error.message);
          }
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
  }, [jobId, reconnectKey]);

  useEffect(() => {
    if (status !== "queued" && status !== "running") {
      return;
    }
    const close = streamJobEvents(jobId, {
      onEvent: (event) => {
        if (seenIdsRef.current.has(event.event_id)) {
          return;
        }
        seenIdsRef.current.add(event.event_id);
        setEvents((current) => [...current, event]);
      },
      onDone: (finalStatus) => setStatus(finalStatus),
      onError: (message) => setError(message),
    });
    return close;
  }, [jobId, status, reconnectKey]);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [events]);

  const stageStatus = (stage: string): "done" | "active" | "pending" | "failed" => {
    if (events.some((event) => event.type === "stage" && event.stage === stage && event.status === "failed")) {
      return "failed";
    }
    if (events.some((event) => event.type === "stage" && event.stage === stage && event.status === "done")) {
      return "done";
    }
    if (events.some((event) => event.type === "stage" && event.stage === stage && event.status === "started")) {
      return "active";
    }
    return "pending";
  };

  const handleRetry = () => {
    setError(null);
    setReconnectKey((key) => key + 1);
  };

  return (
    <div className="progress-view">
      {error && (
        <div className="progress-error" role="alert">
          <p>{error}</p>
          <button type="button" onClick={handleRetry}>
            다시 연결
          </button>
        </div>
      )}

      {status === "completed" && (
        <p className="progress-done">
          생성이 완료되었습니다.{" "}
          <Link href={`/runs/${jobId}/review`}>검토 화면으로 이동 →</Link>
        </p>
      )}

      {status === "queued" && events.length === 0 && !error && (
        <p className="progress-loading">불러오는 중…</p>
      )}

      <div className="progress-grid">
        <section className="progress-stages" aria-label="단계 체크리스트">
          <h2>작업 목록</h2>
          <ol className="stage-list">
            {STAGE_ORDER.map((stage) => {
              const state = stageStatus(stage);
              const stageEvents = events.filter(
                (event) => event.type === "stage" && event.stage === stage,
              );
              return (
                <li key={stage} className={`stage-row stage-${state}`} data-testid={`stage-${stage}`}>
                  <span className="stage-marker">
                    {state === "done" ? "☑" : state === "failed" ? "✕" : state === "active" ? "◐" : "○"}
                  </span>
                  <span className="stage-label">{STAGE_LABELS[stage] ?? stage}</span>
                  {stageEvents.length > 0 && (
                    <span className="stage-message">{stageEvents.at(-1)?.message}</span>
                  )}
                </li>
              );
            })}
          </ol>
        </section>

        <section className="progress-log" ref={logRef} aria-label="LLM 호출 로그">
          <h2>LLM 호출 로그</h2>
          <CallLog events={events} />
        </section>
      </div>
    </div>
  );
}

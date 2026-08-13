import { useMemo } from "react";

import type { JobEvent } from "@/lib/types";

function formatTime(ts: string): string {
  if (!ts) {
    return "";
  }
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleTimeString("ko-KR", { hour12: false });
}

interface StreamGroup {
  key: string;
  role: string;
  model: string;
  schema: string;
  content: string;
  reasoning: string;
  done: boolean;
  summary: string;
}

function buildStreamGroups(events: JobEvent[]): StreamGroup[] {
  const groups = new Map<string, StreamGroup>();
  const callsByKey = new Map<string, JobEvent>();

  for (const event of events) {
    if (event.type === "llm_call") {
      const role = typeof event.data.role === "string" ? event.data.role : "";
      const attempt = typeof event.data.attempts === "number" ? event.data.attempts : 0;
      callsByKey.set(`${role}:${attempt}`, event);
    }
  }

  for (const event of events) {
    if (event.type !== "llm_delta") {
      continue;
    }
    const role = typeof event.data.role === "string" ? event.data.role : "";
    const attempt = typeof event.data.attempt === "number" ? event.data.attempt : 0;
    const key = `${role}:${attempt}`;
    const content = typeof event.data.content === "string" ? event.data.content : "";
    const reasoning = typeof event.data.reasoning === "string" ? event.data.reasoning : "";
    const existing = groups.get(key);
    const done = callsByKey.has(key);
    const call = callsByKey.get(key);
    const callData = call?.data ?? {};
    const summary =
      call && callData.summary && typeof callData.summary === "object"
        ? String((callData.summary as Record<string, unknown>).title ?? "")
        : "";
    if (existing) {
      existing.content += content;
      existing.reasoning += reasoning;
      existing.done = done;
      existing.summary = summary;
      continue;
    }
    groups.set(key, {
      key,
      role,
      model: typeof event.data.model === "string" ? event.data.model : "",
      schema: typeof event.data.schema === "string" ? event.data.schema : "",
      content,
      reasoning,
      done,
      summary,
    });
  }

  return [...groups.values()].sort((a, b) => a.key.localeCompare(b.key));
}

/** LLM 호출 로그 — 완료 호출 요약 + 진행 중 호출의 실시간 스트리밍 응답. */
export function CallLog({ events }: { events: JobEvent[] }) {
  const streams = useMemo(() => buildStreamGroups(events), [events]);
  const calls = events.filter((event) => event.type === "llm_call");

  const activeStreams = streams.filter((stream) => !stream.done);
  const hasStreaming = activeStreams.length > 0;

  if (calls.length === 0 && !hasStreaming) {
    return <p className="call-log-empty">아직 LLM 호출이 없습니다.</p>;
  }

  return (
    <div className="call-log">
      <ol className="call-log-list" data-testid="call-log">
        {calls.map((event) => {
          const data = event.data;
          const summary = data.summary as Record<string, unknown> | undefined;
          const summaryText = summary && typeof summary.title === "string" ? summary.title : "";
          const latency = typeof data.latency_ms === "number" ? data.latency_ms : null;
          const cost = typeof data.cost_usd === "number" ? data.cost_usd : null;
          const model = typeof data.model === "string" ? data.model : "";
          const role = typeof data.role === "string" ? data.role : "";
          const schema = typeof data.schema === "string" ? data.schema : "";
          const errorCode =
            data.error && typeof data.error === "object" && "code" in data.error
              ? String(data.error.code)
              : null;
          return (
            <li key={event.event_id} className={`call-log-row call-log-${event.status}`}>
              <span className="call-log-time">{formatTime(event.ts)}</span>
              <span className="call-log-status">{event.status === "failed" ? "err" : "ok"}</span>
              <code className="call-log-model">{model}</code>
              <span className="call-log-schema">
                {role}·{schema}
              </span>
              {summaryText && <span className="call-log-summary">{summaryText}</span>}
              {errorCode && <span className="call-log-error">{errorCode}</span>}
              <span className="call-log-meta">
                {latency !== null ? `${latency}ms` : ""}
                {cost !== null ? ` · $${cost.toFixed(4)}` : ""}
              </span>
            </li>
          );
        })}
      </ol>

      {hasStreaming && (
        <section className="call-log-streams" data-testid="call-streams">
          <h3>실시간 응답</h3>
          {activeStreams.map((stream) => (
            <article key={stream.key} className="call-stream-row" data-testid="call-stream-row">
              <div className="call-stream-head">
                <span className="call-stream-role">{stream.role}</span>
                <code className="call-log-model">{stream.model}</code>
                <span className="call-stream-cursor" aria-hidden="true" />
              </div>
              {stream.reasoning && (
                <details className="call-stream-reasoning" open>
                  <summary>생각 중…</summary>
                  <pre>{stream.reasoning}</pre>
                </details>
              )}
              {stream.content && <pre className="call-stream-content">{stream.content}</pre>}
            </article>
          ))}
        </section>
      )}
    </div>
  );
}

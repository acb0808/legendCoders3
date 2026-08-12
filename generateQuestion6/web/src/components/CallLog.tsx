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

/** LLM 호출 로그 — 호출된 LLM·결과 요약·지연·비용. */
export function CallLog({ events }: { events: JobEvent[] }) {
  const calls = events.filter((event) => event.type === "llm_call");
  if (calls.length === 0) {
    return <p className="call-log-empty">아직 LLM 호출이 없습니다.</p>;
  }
  return (
    <ol className="call-log" data-testid="call-log">
      {calls.map((event) => {
        const data = event.data;
        const summary = data.summary as Record<string, unknown> | undefined;
        const summaryText =
          summary && typeof summary.title === "string" ? summary.title : "";
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
            <span className="call-log-schema">{role}·{schema}</span>
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
  );
}

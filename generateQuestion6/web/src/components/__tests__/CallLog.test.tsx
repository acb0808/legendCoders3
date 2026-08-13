import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CallLog } from "../CallLog";
import type { JobEvent } from "@/lib/types";

describe("CallLog (T08)", () => {
  it("LLM 호출 이벤트를 모델·요약과 함께 렌더링한다", () => {
    const events: JobEvent[] = [
      {
        event_id: "e1",
        type: "llm_call",
        stage: "ideation",
        status: "done",
        message: "",
        ts: "2026-01-01T00:00:00+00:00",
        data: { role: "ideator", schema: "IdeationOutput", provider: "deepseek", model: "deepseek-v4-flash", ok: true, summary: { title: "질문 역전" }, latency_ms: 100, cost_usd: 0.001 },
      },
    ];
    render(<CallLog events={events} />);
    expect(screen.getByText("deepseek-v4-flash")).toBeInTheDocument();
    expect(screen.getByText("질문 역전")).toBeInTheDocument();
  });

  it("실패 이벤트는 오류 코드를 표시한다", () => {
    const events: JobEvent[] = [
      {
        event_id: "e2",
        type: "llm_call",
        stage: "judge",
        status: "failed",
        message: "",
        ts: "",
        data: { role: "judge", schema: "JudgeOutput", provider: "deepseek", model: "m", ok: false, error: { code: "SCHEMA_VALIDATION" } },
      },
    ];
    render(<CallLog events={events} />);
    expect(screen.getByText("SCHEMA_VALIDATION")).toBeInTheDocument();
  });

  it("llm_delta 를 role·attempt 로 그룹핑해 실시간 누적 표시한다", () => {
    const events: JobEvent[] = [
      {
        event_id: "d1",
        type: "llm_delta",
        stage: "ideation",
        status: "streaming",
        message: "",
        ts: "",
        data: { role: "ideator", attempt: 1, content: "{\"tit", reasoning: "We should" },
      },
      {
        event_id: "d2",
        type: "llm_delta",
        stage: "ideation",
        status: "streaming",
        message: "",
        ts: "",
        data: { role: "ideator", attempt: 1, content: "le\": \"q\"}", reasoning: " think first." },
      },
    ];
    render(<CallLog events={events} />);
    expect(screen.getByTestId("call-streams")).toBeInTheDocument();
    expect(screen.getByText('{"title": "q"}')).toBeInTheDocument();
    expect(screen.getByText("We should think first.")).toBeInTheDocument();
  });

  it("완료된 호출(이후 llm_call)의 스트림은 실시간 패널에 남지 않는다", () => {
    const events: JobEvent[] = [
      {
        event_id: "d1",
        type: "llm_delta",
        stage: "ideation",
        status: "streaming",
        message: "",
        ts: "",
        data: { role: "ideator", attempt: 1, content: "{\"title\": \"q\"}", reasoning: "think" },
      },
      {
        event_id: "c1",
        type: "llm_call",
        stage: "ideation",
        status: "done",
        message: "",
        ts: "",
        data: { role: "ideator", schema: "IdeationOutput", provider: "deepseek", model: "deepseek-v4-flash", attempts: 1, ok: true, summary: { title: "질문 역전" }, latency_ms: 100, cost_usd: 0.001 },
      },
    ];
    render(<CallLog events={events} />);
    expect(screen.queryByTestId("call-streams")).not.toBeInTheDocument();
    expect(screen.getByText("질문 역전")).toBeInTheDocument();
  });
});

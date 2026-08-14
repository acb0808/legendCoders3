import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProgressView } from "../ProgressView";
import * as api from "@/lib/api";
import type { JobEvent } from "@/lib/types";

function makeEvent(overrides: Partial<JobEvent> = {}): JobEvent {
  return {
    event_id: "e1",
    type: "stage",
    stage: "planner",
    status: "done",
    message: "기획 완료",
    ts: "2026-01-01T00:00:00+00:00",
    data: {},
    ...overrides,
  };
}

function makeJob(overrides = {}) {
  return {
    job_id: "run-1",
    run_id: "run-1",
    source: { mode: "text", text: "원문" },
    options: { difficulty_target: "", ideator_count: 3, max_refine: 2 },
    status: "completed",
    events: [makeEvent()],
    error: null,
    created_at: "",
    updated_at: "",
    ...overrides,
  } as never;
}

describe("ProgressView (T08)", () => {
  it("완료된 job 은 검토 화면 링크를 보여준다", async () => {
    vi.spyOn(api, "getJob").mockResolvedValue(makeJob());
    vi.spyOn(api, "streamJobEvents").mockImplementation((_jobId, handlers) => {
      handlers.onDone("completed");
      return () => {};
    });

    render(<ProgressView jobId="run-1" />);
    expect(await screen.findByRole("link", { name: /검토 화면으로 이동/ })).toHaveAttribute(
      "href",
      "/runs/run-1/review",
    );
  });

  it("불러오는 중 상태에서는 로딩 문구를 보여준다", async () => {
    vi.spyOn(api, "getJob").mockResolvedValue(makeJob({ status: "queued", events: [] }));
    vi.spyOn(api, "streamJobEvents").mockImplementation(() => () => {});

    render(<ProgressView jobId="run-1" />);
    expect(await screen.findByText(/불러오는 중/)).toBeInTheDocument();
  });

  it("SSE 로 재생된 이벤트는 중복 표시하지 않는다", async () => {
    const replayed = makeEvent({
      event_id: "llm-1",
      type: "llm_call",
      stage: "generation",
      status: "done",
      message: "후보 생성",
      data: { model: "gpt-4o", role: "critic", schema: "s", latency_ms: 12, cost_usd: 0.001 },
    });
    vi.spyOn(api, "getJob").mockResolvedValue(
      makeJob({ status: "running", events: [replayed] }),
    );
    vi.spyOn(api, "streamJobEvents").mockImplementation((_jobId, handlers) => {
      handlers.onEvent(replayed);
      handlers.onEvent(replayed);
      return () => {};
    });

    render(<ProgressView jobId="run-1" />);
    const callLog = await screen.findByTestId("call-log");
    await waitFor(() => {
      expect(within(callLog).getAllByRole("listitem")).toHaveLength(1);
    });
  });

  it("실패한 job 은 에러 배너를 보여준다", async () => {
    vi.spyOn(api, "getJob").mockResolvedValue(
      makeJob({
        status: "failed",
        events: [],
        error: { message: "boom", code: "AGENT_UNRESOLVED" },
      }),
    );
    vi.spyOn(api, "streamJobEvents").mockImplementation((_jobId, handlers) => {
      handlers.onError("연결 끊김");
      return () => {};
    });

    render(<ProgressView jobId="run-1" />);
    expect(await screen.findByText(/boom/)).toBeInTheDocument();
  });

  it("레퍼런스 레이어 단계가 체크리스트에 표시된다", async () => {
    vi.spyOn(api, "getJob").mockResolvedValue(makeJob());
    vi.spyOn(api, "streamJobEvents").mockImplementation(() => () => {});

    render(<ProgressView jobId="run-1" />);

    expect(await screen.findByTestId("stage-reference")).toHaveTextContent("참조 검색");
    expect(screen.getByTestId("stage-skill_mapping")).toHaveTextContent("스킬 매핑");
    expect(screen.getByTestId("stage-style_align")).toHaveTextContent("스타일 정렬");
  });
});


import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProgressView } from "../ProgressView";
import * as api from "@/lib/api";

function makeEvent(overrides = {}) {
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

describe("ProgressView (T08)", () => {
  it("완료된 job 은 검토 화면 링크를 보여준다", () => {
    vi.spyOn(api, "getJob").mockResolvedValue({
      job_id: "run-1",
      run_id: "run-1",
      source: { mode: "text", text: "원문" },
      options: { difficulty_target: "", ideator_count: 3, max_refine: 2 },
      status: "completed",
      events: [makeEvent()],
      error: null,
      created_at: "",
      updated_at: "",
    } as never);
    vi.spyOn(api, "streamJobEvents").mockImplementation((_jobId, handlers) => {
      handlers.onDone("completed");
      return () => {};
    });

    render(<ProgressView jobId="run-1" />);
    expect(screen.getByRole("link", { name: /검토 화면으로 이동/ })).toHaveAttribute(
      "href",
      "/runs/run-1/review",
    );
  });

  it("실패한 job 은 에러 배너를 보여준다", async () => {
    vi.spyOn(api, "getJob").mockResolvedValue({
      job_id: "run-1",
      run_id: "run-1",
      source: { mode: "text", text: "원문" },
      options: { difficulty_target: "", ideator_count: 3, max_refine: 2 },
      status: "failed",
      events: [],
      error: { message: "boom", code: "AGENT_UNRESOLVED" },
      created_at: "",
      updated_at: "",
    } as never);
    vi.spyOn(api, "streamJobEvents").mockImplementation((_jobId, handlers) => {
      handlers.onError("연결 끊김");
      return () => {};
    });

    render(<ProgressView jobId="run-1" />);
    expect(await screen.findByText(/boom/)).toBeInTheDocument();
  });
});

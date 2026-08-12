import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RunList } from "../RunList";
import type { RunSummary } from "@/lib/types";

function makeRun(overrides: Partial<RunSummary> = {}): RunSummary {
  return {
    run_id: "run-1",
    state: "TOOL_VERIFIED",
    candidate_count: 3,
    verified_count: 2,
    created_at: "2026-01-01T00:00:00+00:00",
    updated_at: "2026-01-01T00:00:00+00:00",
    ...overrides,
  };
}

describe("RunList (index 실행 목록)", () => {
  it("각 실행을 검토 화면 링크로 노출한다", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify([
          makeRun(),
          makeRun({
            run_id: "run-2",
            state: "GENERATED",
            candidate_count: 2,
            verified_count: 1,
          }),
        ]),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(<RunList />);

    await waitFor(() => {
      expect(screen.getByTestId("run-row-run-1")).toBeInTheDocument();
    });
    expect(screen.getByTestId("run-row-run-2")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "run-1" })).toHaveAttribute(
      "href",
      "/runs/run-1/review",
    );
    expect(screen.getByText("TOOL_VERIFIED")).toBeInTheDocument();
    expect(screen.getByText("검증 후보 2 / 전체 3")).toBeInTheDocument();
  });

  it("실행이 없으면 안내 문구를 보여준다", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(<RunList />);

    await waitFor(() => {
      expect(screen.getByText("아직 생성된 실행이 없습니다.")).toBeInTheDocument();
    });
  });

  it("API 오류 시 오류 메시지를 보여준다", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("boom", { status: 500 }),
    );

    render(<RunList />);

    await waitFor(() => {
      expect(screen.getByText(/실행 목록을 불러오지 못했습니다/)).toBeInTheDocument();
    });
  });
});

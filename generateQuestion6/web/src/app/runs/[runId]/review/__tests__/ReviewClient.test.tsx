import { Suspense } from "react";
import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReviewClient } from "../ReviewClient";
import * as api from "@/lib/api";

function makeRun(overrides: Record<string, unknown> = {}) {
  return {
    run_id: "run-1",
    state: "GENERATED",
    source: { mode: "text", text: "원문" },
    candidates: [],
    created_at: "",
    updated_at: "",
    ...overrides,
  } as never;
}

describe("ReviewClient 참조 요약 패널", () => {
  it("reference_summary 가 있으면 참조 요약 패널을 표시한다", async () => {
    vi.spyOn(api, "getRun").mockResolvedValue(
      makeRun({
        reference_summary: {
          exam_patterns: [
            { topic_id: "t1", unit: "도형의 방정식", pattern: "접선의 방정식", source_count: 2 },
          ],
          condition_phrasings: { count: 2, topics: ["도형의 방정식"] },
          style_guide: { unit: "도형의 방정식", justification_vocab: ["따라서"] },
        },
      }),
    );

    await act(async () => {
      render(
        <Suspense fallback={<div>Loading...</div>}>
          <ReviewClient runIdPromise={Promise.resolve({ runId: "run-1" })} />
        </Suspense>,
      );
    });

    const panel = await screen.findByTestId("reference-summary");
    expect(panel).toHaveTextContent("접선의 방정식");
    expect(panel).toHaveTextContent("2건");
    expect(panel).toHaveTextContent("따라서");
  });

  it("reference_summary 가 없으면 패널을 표시하지 않는다", async () => {
    vi.spyOn(api, "getRun").mockResolvedValue(makeRun());

    await act(async () => {
      render(
        <Suspense fallback={<div>Loading...</div>}>
          <ReviewClient runIdPromise={Promise.resolve({ runId: "run-1" })} />
        </Suspense>,
      );
    });

    expect(await screen.findByText(/후보 비교/)).toBeInTheDocument();
    expect(screen.queryByTestId("reference-summary")).not.toBeInTheDocument();
  });
});



import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProblemPicker } from "../ProblemPicker";
import * as api from "@/lib/api";

describe("ProblemPicker (T08)", () => {
  it("검색어로 문제를 필터링해 선택할 수 있다", async () => {
    vi.spyOn(api, "listProblems").mockResolvedValue([
      { problem_id: "p1", title: "포물선", text: "포물선 문제", source: "manual", source_run_id: null, created_at: "" },
      { problem_id: "p2", title: "직선", text: "직선 문제", source: "manual", source_run_id: null, created_at: "" },
    ]);
    const onSelect = vi.fn();
    render(<ProblemPicker value="" onSelect={onSelect} />);
    await waitFor(() => expect(screen.getByRole("combobox")).toBeInTheDocument());
    await userEvent.type(screen.getByPlaceholderText(/검색/), "포물선");
    await userEvent.click(screen.getByText("포물선 문제"));
    expect(onSelect).toHaveBeenCalledWith("p1");
  });
});

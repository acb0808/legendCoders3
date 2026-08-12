import { render, screen } from "@testing-library/react";
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
    await screen.findByRole("option", { name: "포물선 — 포물선 문제" });
    expect(screen.getAllByRole("option")).toHaveLength(3); // placeholder + 2
    await userEvent.type(screen.getByPlaceholderText(/검색/), "포물선");
    const filtered = screen.getAllByRole("option");
    expect(filtered.map((o) => o.textContent)).toEqual(["문제를 선택하세요", "포물선 — 포물선 문제"]);
    await userEvent.selectOptions(screen.getByRole("combobox"), "p1");
    expect(onSelect).toHaveBeenCalledWith("p1");
  });

  it("문제 목록을 불러오지 못하면 오류를 표시한다", async () => {
    vi.spyOn(api, "listProblems").mockRejectedValue(new Error("서버 오류"));
    render(<ProblemPicker value="" onSelect={() => {}} />);
    const alert = await screen.findByText(/서버 오류/);
    expect(alert).toBeInTheDocument();
    expect(alert.className).toBe("problems-error");
  });
});

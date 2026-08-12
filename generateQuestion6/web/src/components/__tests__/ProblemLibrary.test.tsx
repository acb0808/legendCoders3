import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProblemLibrary } from "../ProblemLibrary";
import * as api from "@/lib/api";

describe("ProblemLibrary (T08)", () => {
  it("문제를 목록으로 보여주고 삭제할 수 있다", async () => {
    vi.spyOn(api, "listProblems").mockResolvedValue([
      { problem_id: "p1", title: "광명북고 Q19", text: "포물선 문제", source: "manual", source_run_id: null, created_at: "" },
    ]);
    const del = vi.spyOn(api, "deleteProblem").mockResolvedValue();
    render(<ProblemLibrary />);
    await waitFor(() => expect(screen.getByText("광명북고 Q19")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /삭제/ }));
    await waitFor(() => expect(del).toHaveBeenCalledWith("p1"));
  });

  it("새 문제를 등록한다", async () => {
    vi.spyOn(api, "listProblems").mockResolvedValue([]);
    vi.spyOn(api, "registerProblem").mockResolvedValue({
      problem_id: "p2", title: "", text: "새 문제", source: "manual", source_run_id: null, created_at: "",
    });
    render(<ProblemLibrary />);
    await userEvent.type(screen.getByLabelText(/새 문제 텍스트/), "새 문제 본문");
    await userEvent.click(screen.getByRole("button", { name: /등록/ }));
    await waitFor(() =>
      expect(api.registerProblem).toHaveBeenCalledWith(expect.objectContaining({ text: "새 문제 본문" })),
    );
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CreateForm } from "../CreateForm";
import * as api from "@/lib/api";

describe("CreateForm (T08 생성 화면)", () => {
  it("텍스트 모드에서 생성 시작을 요청한다", async () => {
    const push = vi.fn();
    vi.spyOn(api, "createGeneration").mockResolvedValue({
      job_id: "run-1",
      run_id: "run-1",
      status: "queued",
    });
    vi.spyOn(api, "listProblems").mockResolvedValue([]);

    render(<CreateForm onNavigate={push} />);

    await userEvent.type(screen.getByLabelText(/문제 본문/), "포물선 y=x^2 의 접선");
    await userEvent.click(screen.getByRole("button", { name: /생성 시작/ }));

    await waitFor(() => {
      expect(api.createGeneration).toHaveBeenCalledWith(
        expect.objectContaining({ mode: "text", text: "포물선 y=x^2 의 접선" }),
        expect.objectContaining({ ideator_count: 3 }),
      );
    });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/runs/run-1/progress"));
  });

  it("빈 텍스트면 생성하지 않는다", async () => {
    vi.spyOn(api, "listProblems").mockResolvedValue([]);
    const create = vi.spyOn(api, "createGeneration").mockResolvedValue({
      job_id: "r",
      run_id: "r",
      status: "queued",
    });
    render(<CreateForm onNavigate={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /생성 시작/ }));
    expect(create).not.toHaveBeenCalled();
  });
});

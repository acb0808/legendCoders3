import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CandidateList } from "../CandidateList";
import { EvidencePanel } from "../EvidencePanel";
import { ReviewActions, hasRequiredArtifacts } from "../ReviewActions";
import type { Candidate, CheckResult } from "@/lib/types";

function makeCandidate(overrides: Partial<Candidate> = {}): Candidate {
  return {
    candidate_id: "c1",
    plan_id: "plan-1",
    problem_text: "점 (3, 4)에서 원 x^2+y^2=25에 그은 접선의 방정식을 구하시오.",
    formalization: { symbols: ["x", "y"], constraints: [], goal: "접선의 방정식" },
    final_answer_claim: "3x + 4y = 25",
    solution_steps: [{ step_id: "s1", statement: "거리 조건 사용" }],
    transformation_evidence: [{ dimension: "representation" }],
    verification_status: "PASS",
    rubric: {
      graph_id: "g",
      items: [{ node_id: "n1", score: 4, description: "접선 도출" }],
      total_points: 4,
      derived_from_verified: true,
    },
    evidence: {
      evidence_id: "e",
      candidate_id: "c1",
      checks: [
        {
          check_id: "sympy-main",
          kind: "fixed",
          status: "PASS",
          critical: true,
          evidence: { distance: "equal" },
        },
      ],
    },
    ...overrides,
  };
}

function makeCheck(status: CheckResult["status"]): CheckResult {
  return {
    check_id: `check-${status}`,
    kind: "fixed",
    status,
    critical: true,
    evidence: {},
  };
}

describe("T06.4-UT1 검증 후보만 노출", () => {
  it("UNVERIFIED·FAIL·UNRESOLVED 후보는 카드 목록에 나타나지 않는다", () => {
    const candidates = [
      makeCandidate({ candidate_id: "pass", verification_status: "PASS" }),
      makeCandidate({ candidate_id: "unverified", verification_status: "UNVERIFIED" }),
      makeCandidate({ candidate_id: "fail", verification_status: "FAIL" }),
      makeCandidate({ candidate_id: "unresolved", verification_status: "UNRESOLVED" }),
    ];

    render(<CandidateList candidates={candidates} onDecide={vi.fn()} />);

    expect(screen.getByTestId("candidate-card-pass")).toBeInTheDocument();
    expect(screen.queryByTestId("candidate-card-unverified")).not.toBeInTheDocument();
    expect(screen.queryByTestId("candidate-card-fail")).not.toBeInTheDocument();
    expect(screen.queryByTestId("candidate-card-unresolved")).not.toBeInTheDocument();
  });
});

describe("T06.4-UT2 필수 산출물 누락 시 승인 비활성화", () => {
  it("모든 필수 필드가 있으면 승인 버튼이 활성화된다", () => {
    const candidate = makeCandidate();
    render(<ReviewActions candidate={candidate} onDecide={vi.fn()} />);

    const approve = screen.getByRole("button", { name: "승인" });
    expect(approve).not.toBeDisabled();
  });

  it("필수 필드가 누락되면 승인 버튼이 비활성화된다", () => {
    const missing: Partial<Candidate>[] = [
      { problem_text: "" },
      { final_answer_claim: "" },
      { solution_steps: [] },
      { rubric: null },
      { transformation_evidence: [] },
      { evidence: null },
    ];
    for (const patch of missing) {
      const candidate = makeCandidate(patch);
      expect(hasRequiredArtifacts(candidate)).toBe(false);
      const { unmount } = render(<ReviewActions candidate={candidate} onDecide={vi.fn()} />);
      expect(screen.getByRole("button", { name: "승인" })).toBeDisabled();
      unmount();
    }
  });
});

describe("T06.4-UT3 반려 사유 필수", () => {
  it("사유 없이 반려를 확정할 수 없다", () => {
    const onDecide = vi.fn();
    render(<ReviewActions candidate={makeCandidate()} onDecide={onDecide} />);

    fireEvent.click(screen.getByRole("button", { name: "반려" }));
    const confirm = screen.getByRole("button", { name: "반려 확정" });
    expect(confirm).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/반려 사유/), { target: { value: "MATH_ERROR" } });
    expect(confirm).not.toBeDisabled();

    fireEvent.click(confirm);
    expect(onDecide).toHaveBeenCalledWith("rejected", "MATH_ERROR");
  });
});

describe("T06.4-UT4 중복 승인 차단", () => {
  it("승인 후 같은 후보를 다시 승인해 중복 이벤트를 만들지 않는다", () => {
    const onDecide = vi.fn();
    render(<ReviewActions candidate={makeCandidate()} onDecide={onDecide} />);

    fireEvent.click(screen.getByRole("button", { name: "승인" }));
    expect(onDecide).toHaveBeenCalledTimes(1);
    expect(screen.getByText("승인됨")).toBeInTheDocument();

    // 결정 후 액션 버튼이 사라지므로 다시 승인할 수 없다.
    expect(screen.queryByRole("button", { name: "승인" })).not.toBeInTheDocument();
  });
});

describe("T06.4-UT5 상태는 항상 보이고 상세는 접을 수 있다", () => {
  it("상세를 접어도 PASS·FAIL·UNRESOLVED 상태는 항상 보인다", () => {
    const evidence = {
      evidence_id: "e",
      candidate_id: "c1",
      checks: [makeCheck("PASS"), makeCheck("FAIL"), makeCheck("UNRESOLVED")],
    };

    const { container } = render(<EvidencePanel evidence={evidence} />);

    // 상태 요약이 항상 렌더링된다.
    expect(screen.getByLabelText("검증 상태 요약")).toBeInTheDocument();
    expect(container.querySelectorAll('[data-status="PASS"]').length).toBeGreaterThan(0);
    expect(container.querySelectorAll('[data-status="FAIL"]').length).toBeGreaterThan(0);
    expect(container.querySelectorAll('[data-status="UNRESOLVED"]').length).toBeGreaterThan(0);

    // 상세는 기본적으로 접혀 있다가 토글로 펼친다.
    expect(screen.queryByText("근거")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "상세 증거 보기" }));
    expect(screen.getAllByText("근거").length).toBeGreaterThan(0);
  });
});

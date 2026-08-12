"use client";

import { useState } from "react";

import { REJECT_REASON_CODES } from "@/lib/types";
import type { Candidate, Decision } from "@/lib/types";

/** 승인·반려 액션 — 필수 산출물·증거가 없으면 승인 불가, 반려는 사유 필수, 중복 승인 차단. */
export function ReviewActions({
  candidate,
  onDecide,
  disabled = false,
}: {
  candidate: Candidate;
  onDecide: (decision: Decision, rejectReasonCode: string | null) => void;
  disabled?: boolean;
}) {
  const [rejectReason, setRejectReason] = useState<string>("");
  const [decided, setDecided] = useState<Decision | null>(null);
  const [isRejecting, setIsRejecting] = useState(false);

  const canApprove = hasRequiredArtifacts(candidate) && !disabled && decided === null;
  const canReject = rejectReason.trim() !== "" && !disabled && decided === null;

  const decide = (decision: Decision) => {
    if (decision === "rejected" && !canReject) {
      return;
    }
    if (decision === "approved" && !canApprove) {
      return;
    }
    onDecide(decision, decision === "rejected" ? rejectReason : null);
    setDecided(decision);
    setIsRejecting(false);
  };

  if (decided !== null) {
    return (
      <div className="review-actions" data-testid="review-actions">
        <p className="decision-badge" data-decision={decided}>
          {decided === "approved" ? "승인됨" : "반려됨"}
        </p>
      </div>
    );
  }

  return (
    <div className="review-actions" data-testid="review-actions">
      <div className="review-actions-row">
        <button
          type="button"
          className="button-approve"
          onClick={() => decide("approved")}
          disabled={!canApprove}
          aria-disabled={!canApprove}
          title={canApprove ? "승인" : "필수 산출물·증거가 없어 승인할 수 없습니다"}
        >
          승인
        </button>
        <button
          type="button"
          className="button-reject"
          onClick={() => setIsRejecting((value) => !value)}
          disabled={disabled || decided !== null}
          aria-expanded={isRejecting}
        >
          반려
        </button>
      </div>

      {isRejecting && (
        <div className="reject-form">
          <label htmlFor={`reject-reason-${candidate.candidate_id}`}>반려 사유</label>
          <select
            id={`reject-reason-${candidate.candidate_id}`}
            value={rejectReason}
            onChange={(event) => setRejectReason(event.target.value)}
          >
            <option value="">사유를 선택하세요</option>
            {REJECT_REASON_CODES.map((reason) => (
              <option key={reason.code} value={reason.code}>
                {reason.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="button-reject-confirm"
            onClick={() => decide("rejected")}
            disabled={!canReject}
          >
            반려 확정
          </button>
        </div>
      )}
    </div>
  );
}

/** 승인 가능 조건: 문제·답·해설·부분점수·변형 설명·증거가 모두 있어야 한다. (T06.4-UT2) */
export function hasRequiredArtifacts(candidate: Candidate): boolean {
  const hasProblem = candidate.problem_text.trim().length > 0;
  const hasAnswer = candidate.final_answer_claim.trim().length > 0;
  const hasSolution = candidate.solution_steps.length > 0;
  const hasRubric = (candidate.rubric?.items.length ?? 0) > 0;
  const hasTransformation = candidate.transformation_evidence.length > 0;
  const hasEvidence = (candidate.evidence?.checks.length ?? 0) > 0;
  return (
    hasProblem && hasAnswer && hasSolution && hasRubric && hasTransformation && hasEvidence
  );
}

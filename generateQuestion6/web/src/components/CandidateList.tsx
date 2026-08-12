import { verifiedCandidates } from "@/lib/api";
import type { Candidate, Decision } from "@/lib/types";
import { CandidateCard } from "./CandidateCard";

/** 검증을 통과한 후보만 목록에 노출한다. (T06.4-UT1) */
export function CandidateList({
  candidates,
  onDecide,
}: {
  candidates: Candidate[];
  onDecide: (candidateId: string, decision: Decision, rejectReasonCode: string | null) => void;
}) {
  const verified = verifiedCandidates(candidates);

  if (verified.length === 0) {
    return <p className="candidates-empty">검증을 통과한 후보가 없습니다.</p>;
  }

  return (
    <div className="candidate-list" data-testid="candidate-list">
      <p className="candidate-list-count">검증 후보 {verified.length}건</p>
      <div className="candidate-grid">
        {verified.map((candidate) => (
          <CandidateCard
            key={candidate.candidate_id}
            candidate={candidate}
            onDecide={(decision, reason) => onDecide(candidate.candidate_id, decision, reason)}
          />
        ))}
      </div>
    </div>
  );
}

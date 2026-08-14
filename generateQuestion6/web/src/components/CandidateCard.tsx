import { EvidencePanel } from "./EvidencePanel";
import { ReviewActions } from "./ReviewActions";
import { RubricView } from "./RubricView";
import { LatexText } from "@/lib/latex";
import type { Candidate, Decision, TransformationEvidence } from "@/lib/types";

function skillForStep(
  evidence: TransformationEvidence[],
  stepId: string,
): { skill_id: string; concept_name?: string } | null {
  const entry = evidence.find(
    (e) => e.dimension === "skill_mapping" && e.step_id === stepId,
  );
  if (!entry || entry.skill_id == null) {
    return null;
  }
  return { skill_id: entry.skill_id, concept_name: entry.concept_name };
}

/** 후보 카드 — 문제·답·해설·루브릭·변형 차원·검증 증거를 같은 구조로 비교한다. */
export function CandidateCard({
  candidate,
  onDecide,
}: {
  candidate: Candidate;
  onDecide: (decision: Decision, rejectReasonCode: string | null) => void;
}) {
  return (
    <article className="candidate-card" data-testid={`candidate-card-${candidate.candidate_id}`}>
      <header className="candidate-head">
        <h3 className="candidate-title">
          <span className="candidate-kicker">후보</span> {candidate.candidate_id}
          {candidate.style_aligned ? (
            <span className="style-align-badge">스타일 정렬됨</span>
          ) : null}
        </h3>
        <span className="candidate-plan">계획 {candidate.plan_id}</span>
      </header>

      <section aria-label="문제 본문" className="card-section">
        <h4 className="card-section-title">문제</h4>
        <p className="candidate-problem">
          <LatexText text={candidate.problem_text} />
        </p>
      </section>

      <section aria-label="최종 답" className="card-section">
        <h4 className="card-section-title">최종 답</h4>
        <p className="candidate-answer">
          <LatexText text={candidate.final_answer_claim} />
        </p>
      </section>

      <section aria-label="단계별 해설" className="card-section">
        <h4 className="card-section-title">해설</h4>
        <ol className="candidate-solution">
          {candidate.solution_steps.map((step, index) => {
            const skill = skillForStep(candidate.transformation_evidence, step.step_id);
            return (
              <li key={step.step_id}>
                <span className="solution-index">{index + 1}</span>
                <span className="solution-statement">
                  <LatexText text={step.statement} />
                </span>
                {skill ? (
                  <span className="skill-badge">
                    skill {skill.skill_id} · {skill.concept_name ?? "개념"}
                  </span>
                ) : null}
              </li>
            );
          })}
        </ol>
      </section>

      <RubricView rubric={candidate.rubric} />

      <section aria-label="변형 설명" className="card-section">
        <h4 className="card-section-title">변형 설명</h4>
        <ul className="candidate-transformation">
          {candidate.transformation_evidence.map((entry, index) =>
            entry.dimension === "skill_mapping" ? (
              <li key={`${candidate.candidate_id}-t${index}`}>
                <span className="transform-dot" />
                단계 {entry.step_id} →{" "}
                {entry.skill_id
                  ? `skill ${entry.skill_id} · ${entry.concept_name ?? "개념"}`
                  : "매핑 없음"}
              </li>
            ) : (
              <li key={`${candidate.candidate_id}-t${index}`}>
                <span className="transform-dot" />
                {entry.dimension}
              </li>
            ),
          )}
        </ul>
      </section>

      <EvidencePanel evidence={candidate.evidence} />

      <ReviewActions candidate={candidate} onDecide={onDecide} />
    </article>
  );
}


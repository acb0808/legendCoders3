/** 교사 검토 화면 공용 데이터 타입 (T06.4). */

export type VerificationStatus = "UNVERIFIED" | "PASS" | "FAIL" | "UNRESOLVED";

export type CheckStatus = "PASS" | "FAIL" | "UNRESOLVED";

export interface CheckResult {
  check_id: string;
  kind: "fixed" | "sandbox" | "blind" | "counterexample" | "novelty" | "scope";
  status: CheckStatus;
  critical: boolean;
  counterexample?: Record<string, unknown> | null;
  evidence?: Record<string, unknown>;
  tool_version?: string | null;
  code_version?: string | null;
}

export interface ValidationEvidence {
  evidence_id: string;
  candidate_id: string;
  checks: CheckResult[];
  code_version?: string | null;
  tool_versions?: Record<string, string>;
  input_hashes?: Record<string, string>;
}

export interface RubricItem {
  node_id: string;
  score: number;
  description: string;
  equivalent_expressions?: string[];
  common_errors?: string[];
  alternative_paths?: string[];
}

export interface Rubric {
  graph_id: string;
  items: RubricItem[];
  total_points: number;
  derived_from_verified: boolean;
}

export interface SolutionStep {
  step_id: string;
  statement: string;
  justification?: string;
}

export interface Candidate {
  candidate_id: string;
  plan_id: string;
  problem_text: string;
  formalization: {
    symbols: string[];
    constraints: string[];
    goal: string;
  };
  final_answer_claim: string;
  solution_steps: SolutionStep[];
  transformation_evidence: { dimension: string }[];
  verification_status: VerificationStatus;
  validation_ref?: string | null;
  rubric?: Rubric | null;
  evidence?: ValidationEvidence | null;
}

export type Decision = "approved" | "rejected";

export interface RunDecisionEvent {
  run_id: string;
  candidate_id: string;
  decision: Decision;
  reject_reason_code?: string | null;
  decided_at: string;
}

export interface GenerationRun {
  run_id: string;
  state: string;
  candidates: Candidate[];
  created_at: string;
  updated_at: string;
}

export interface RunSummary {
  run_id: string;
  state: string;
  candidate_count: number;
  verified_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export const REJECT_REASON_CODES = [
  { code: "MATH_ERROR", label: "수학적 오류" },
  { code: "SCOPE_VIOLATION", label: "범위 이탈" },
  { code: "COPY", label: "원문 복제" },
  { code: "LOW_QUALITY", label: "품질 부족" },
  { code: "INCOMPLETE", label: "산출물 누락" },
  { code: "OTHER", label: "기타" },
] as const;

/** 생성 작업·문제 라이브러리 (T08). */

export type JobStatus = "queued" | "running" | "completed" | "failed";

export type JobEventType = "stage" | "llm_call" | "llm_delta";

export type JobEventStatus = "started" | "done" | "failed" | "streaming";

export interface JobEvent {
  event_id: string;
  type: JobEventType;
  stage: string;
  status: JobEventStatus;
  message: string;
  candidate_id?: string | null;
  ts: string;
  data: Record<string, unknown>;
}

export interface CreateOptions {
  difficulty_target: string;
  ideator_count: number;
  max_refine: number;
}

export interface SourcePayload {
  mode: "text" | "problem";
  text?: string | null;
  problem_id?: string | null;
}

export interface GenerationResult {
  job_id: string;
  run_id: string;
  status: JobStatus;
}

export interface GenerationJob {
  job_id: string;
  run_id: string;
  source: { mode: "text" | "problem"; text: string; label?: string };
  options: CreateOptions;
  status: JobStatus;
  events: JobEvent[];
  error?: { message: string; code: string } | null;
  report?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface Problem {
  problem_id: string;
  title: string;
  text: string;
  source: "manual" | "approved";
  source_run_id?: string | null;
  text_hash?: string;
  created_at: string;
}

export interface ProblemRequest {
  text: string;
  title?: string;
  source?: "manual" | "approved";
  source_run_id?: string | null;
}

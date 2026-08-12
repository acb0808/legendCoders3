/** 백엔드 FastAPI 와 통신하는 클라이언트 (T06.4). */

import type {
  Candidate,
  CreateOptions,
  Decision,
  GenerationJob,
  GenerationResult,
  GenerationRun,
  JobEvent,
  JobStatus,
  Problem,
  ProblemRequest,
  RunDecisionEvent,
  RunSummary,
  SourcePayload,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API 오류 ${response.status}: ${body.slice(0, 200)}`);
  }
  return (await response.json()) as T;
}

export async function listRuns(): Promise<RunSummary[]> {
  return requestJson<RunSummary[]>("/api/runs");
}

export async function getRun(runId: string): Promise<GenerationRun> {
  return requestJson<GenerationRun>(`/api/runs/${runId}`);
}

export async function postDecision(
  runId: string,
  candidateId: string,
  decision: Decision,
  rejectReasonCode: string | null = null,
): Promise<RunDecisionEvent> {
  return requestJson<RunDecisionEvent>(`/api/runs/${runId}/candidates/${candidateId}/decision`, {
    method: "POST",
    body: JSON.stringify({
      decision,
      reject_reason_code: decision === "rejected" ? rejectReasonCode : null,
    }),
  });
}

/** 검증(PASS)을 통과한 후보만 노출한다. (T06.4-UT1) */
export function verifiedCandidates(candidates: Candidate[]): Candidate[] {
  return candidates.filter((candidate) => candidate.verification_status === "PASS");
}

export async function createGeneration(
  source: SourcePayload,
  options: CreateOptions,
): Promise<GenerationResult> {
  return requestJson<GenerationResult>("/api/generations", {
    method: "POST",
    body: JSON.stringify({ source, options }),
  });
}

export async function getJob(jobId: string): Promise<GenerationJob> {
  return requestJson<GenerationJob>(`/api/generations/${encodeURIComponent(jobId)}`);
}

export function streamJobEvents(
  jobId: string,
  handlers: {
    onEvent: (event: JobEvent) => void;
    onDone: (status: JobStatus) => void;
    onError: (message: string) => void;
  },
): () => void {
  const source = new EventSource(`${API_BASE}/api/generations/${encodeURIComponent(jobId)}/events`);
  source.addEventListener("done", (event) => {
    handlers.onDone((event as MessageEvent).data as JobStatus);
    source.close();
  });
  source.onmessage = (event) => {
    try {
      handlers.onEvent(JSON.parse(event.data) as JobEvent);
    } catch {
      /* 비정상 프레임 무시 */
    }
  };
  source.onerror = () => {
    handlers.onError("진행 스트림 연결이 끊어졌습니다");
    source.close();
  };
  return () => source.close();
}

export async function listProblems(): Promise<Problem[]> {
  return requestJson<Problem[]>("/api/problems");
}

export async function registerProblem(payload: ProblemRequest): Promise<Problem> {
  return requestJson<Problem>("/api/problems", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteProblem(problemId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/problems/${encodeURIComponent(problemId)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API 오류 ${response.status}: ${body.slice(0, 200)}`);
  }
}

export async function listApproved(): Promise<Problem[]> {
  return requestJson<Problem[]>("/api/approved");
}

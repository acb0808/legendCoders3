import { describe, expect, it, vi } from "vitest";

import {
  createGeneration,
  deleteProblem,
  getJob,
  listApproved,
  listProblems,
  registerProblem,
  streamJobEvents,
  verifiedCandidates,
} from "./api";
import type { Candidate, Problem } from "./types";

function makeProblem(overrides: Partial<Problem> = {}): Problem {
  return {
    problem_id: "problem-1",
    title: "T",
    text: "본문",
    source: "manual",
    source_run_id: null,
    created_at: "2026-01-01T00:00:00+00:00",
    ...overrides,
  };
}

function makeCandidate(overrides: Partial<Candidate> = {}): Candidate {
  return {
    candidate_id: "c1",
    plan_id: "plan-1",
    problem_text: "문제 본문",
    formalization: { symbols: ["x"], constraints: [], goal: "접선의 방정식" },
    final_answer_claim: "답",
    solution_steps: [{ step_id: "s1", statement: "단계" }],
    transformation_evidence: [{ dimension: "representation" }],
    verification_status: "PASS",
    ...overrides,
  };
}

describe("verifiedCandidates (T06.4-UT1)", () => {
  it("검증을 통과한 후보만 반환한다", () => {
    const candidates = [
      makeCandidate({ candidate_id: "a", verification_status: "PASS" }),
      makeCandidate({ candidate_id: "b", verification_status: "UNVERIFIED" }),
      makeCandidate({ candidate_id: "c", verification_status: "FAIL" }),
      makeCandidate({ candidate_id: "d", verification_status: "UNRESOLVED" }),
    ];

    const shown = verifiedCandidates(candidates);

    expect(shown.map((c) => c.candidate_id)).toEqual(["a"]);
  });
});

describe("생성 작업·문제 라이브러리 API (T08)", () => {
  it("createGeneration 은 POST 를 보내고 결과를 반환한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ job_id: "run-1", run_id: "run-1", status: "queued" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock);

    const result = await createGeneration(
      { mode: "text", text: "원문" },
      { difficulty_target: "중상", ideator_count: 3, max_refine: 2 },
    );
    expect(result.job_id).toBe("run-1");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/generations"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("getJob 은 작업 상태와 이벤트를 반환한다", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          job_id: "run-1",
          run_id: "run-1",
          status: "completed",
          events: [],
          error: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const job = await getJob("run-1");
    expect(job.status).toBe("completed");
  });

  it("문제 라이브러리 CRUD 가 동작한다", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([makeProblem()]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const problems = await listProblems();
    expect(problems).toHaveLength(1);

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(makeProblem()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const created = await registerProblem({ text: "새 문제" });
    expect(created.problem_id).toBe("problem-1");

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([makeProblem({ source: "approved" })]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const approved = await listApproved();
    expect(approved[0]?.source).toBe("approved");
  });

  it("deleteProblem 은 DELETE 를 보낸다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock);
    await deleteProblem("problem-1");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/problems/problem-1"),
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("streamJobEvents 는 SSE 를 열고 정리 함수를 반환한다", () => {
    const close = vi.fn();
    class FakeEventSource {
      static instances: FakeEventSource[] = [];
      handlers: Record<string, ((event: MessageEvent) => void)[]> = {};
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(public url: string) {
        FakeEventSource.instances.push(this);
      }
      addEventListener(type: string, handler: (event: MessageEvent) => void) {
        (this.handlers[type] ??= []).push(handler);
      }
      close() {
        close();
      }
    }
    const original = globalThis.EventSource;
    (globalThis as Record<string, unknown>).EventSource = FakeEventSource;

    const onEvent = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();
    const cleanup = streamJobEvents("run-1", { onEvent, onDone, onError });

    const es = FakeEventSource.instances[0]!;
    expect(es.url).toContain("/api/generations/run-1/events");

    es.handlers["done"]![0]!(new MessageEvent("done", { data: "completed" }));
    expect(onDone).toHaveBeenCalledWith("completed");

    cleanup();
    expect(close).toHaveBeenCalled();
    (globalThis as Record<string, unknown>).EventSource = original;
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
import type { Candidate, JobEvent, Problem } from "./types";

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

  describe("streamJobEvents SSE (T08)", () => {
    class FakeEventSource {
      static instances: FakeEventSource[] = [];
      handlers: Record<string, ((event: MessageEvent) => void)[]> = {};
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: (() => void) | null = null;
      closed = false;
      constructor(public url: string) {
        FakeEventSource.instances.push(this);
      }
      addEventListener(type: string, handler: (event: MessageEvent) => void) {
        (this.handlers[type] ??= []).push(handler);
      }
      close() {
        this.closed = true;
      }
    }

    function fireOnMessage(es: FakeEventSource, data: unknown) {
      es.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
    }

    let originalEventSource: typeof EventSource;

    beforeEach(() => {
      originalEventSource = globalThis.EventSource;
      FakeEventSource.instances = [];
      (globalThis as Record<string, unknown>).EventSource = FakeEventSource;
    });

    afterEach(() => {
      (globalThis as Record<string, unknown>).EventSource = originalEventSource;
    });

    it("SSE 를 열고 정리 함수를 반환한다", () => {
      const onEvent = vi.fn();
      const onDone = vi.fn();
      const onError = vi.fn();
      const cleanup = streamJobEvents("run-1", { onEvent, onDone, onError });

      const es = FakeEventSource.instances[0]!;
      expect(es.url).toContain("/api/generations/run-1/events");

      cleanup();
      expect(es.closed).toBe(true);
    });

    it("done 이벤트는 onDone 을 호출하고 소스를 닫는다", () => {
      const onEvent = vi.fn();
      const onDone = vi.fn();
      const onError = vi.fn();
      streamJobEvents("run-1", { onEvent, onDone, onError });
      const es = FakeEventSource.instances[0]!;

      es.handlers["done"]![0]!(new MessageEvent("done", { data: "completed" }));

      expect(onDone).toHaveBeenCalledWith("completed");
      expect(es.closed).toBe(true);
      expect(onEvent).not.toHaveBeenCalled();
    });

    it("onmessage 의 llm_call 이벤트를 파싱해 onEvent 로 전달한다", () => {
      const onEvent = vi.fn();
      const onDone = vi.fn();
      const onError = vi.fn();
      streamJobEvents("run-1", { onEvent, onDone, onError });
      const es = FakeEventSource.instances[0]!;

      const event: JobEvent = {
        event_id: "e1",
        type: "llm_call",
        stage: "초안 작성",
        status: "started",
        message: "LLM 호출 시작",
        ts: "2026-01-01T00:00:00+00:00",
        data: {},
      };
      fireOnMessage(es, event);

      expect(onEvent).toHaveBeenCalledWith(event);
      expect(onDone).not.toHaveBeenCalled();
    });

    it("done 이벤트는 onEvent 를 중복 발화하지 않는다", () => {
      const onEvent = vi.fn();
      const onDone = vi.fn();
      const onError = vi.fn();
      streamJobEvents("run-1", { onEvent, onDone, onError });
      const es = FakeEventSource.instances[0]!;

      const event: JobEvent = {
        event_id: "e1",
        type: "llm_call",
        stage: "초안 작성",
        status: "done",
        message: "완료",
        ts: "2026-01-01T00:00:00+00:00",
        data: {},
      };
      fireOnMessage(es, event);
      es.handlers["done"]![0]!(new MessageEvent("done", { data: "completed" }));

      expect(onEvent).toHaveBeenCalledTimes(1);
      expect(onDone).toHaveBeenCalledWith("completed");
    });

    it("비정상 JSON 프레임은 던지지 않고 무시한다", () => {
      const onEvent = vi.fn();
      const onDone = vi.fn();
      const onError = vi.fn();
      streamJobEvents("run-1", { onEvent, onDone, onError });
      const es = FakeEventSource.instances[0]!;

      expect(() => {
        es.onmessage?.({ data: "{not json" } as MessageEvent);
      }).not.toThrow();
      expect(onEvent).not.toHaveBeenCalled();
    });

    it("onerror 는 안내 문구를 전달하고 소스를 닫는다", () => {
      const onEvent = vi.fn();
      const onDone = vi.fn();
      const onError = vi.fn();
      streamJobEvents("run-1", { onEvent, onDone, onError });
      const es = FakeEventSource.instances[0]!;

      es.onerror?.();

      expect(onError).toHaveBeenCalledWith("진행 스트림 연결이 끊어졌습니다");
      expect(es.closed).toBe(true);
    });
  });
});

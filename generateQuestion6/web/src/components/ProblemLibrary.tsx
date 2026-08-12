"use client";

import { useEffect, useState } from "react";

import { deleteProblem, listProblems, registerProblem } from "@/lib/api";
import type { Problem } from "@/lib/types";

/** 문제 라이브러리 관리 — 목록·등록·삭제. */
export function ProblemLibrary() {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    listProblems()
      .then(setProblems)
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : String(reason)),
      );
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleRegister = async () => {
    if (!text.trim()) {
      return;
    }
    try {
      await registerProblem({ text: text.trim(), title: title.trim() });
      setText("");
      setTitle("");
      refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  const handleDelete = async (problemId: string) => {
    try {
      await deleteProblem(problemId);
      refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  return (
    <div className="problem-library">
      {error && <p className="problems-error">{error}</p>}

      <section className="problems-register">
        <h2>새 문제 등록</h2>
        <input
          aria-label="새 문제 제목"
          placeholder="제목 (선택)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          aria-label="새 문제 텍스트"
          placeholder="문제 본문"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
        />
        <button type="button" className="button-register" onClick={handleRegister} disabled={!text.trim()}>
          등록
        </button>
      </section>

      <section className="problems-list">
        <h2>문제 목록</h2>
        {problems.length === 0 ? (
          <p className="problems-empty">등록된 문제가 없습니다.</p>
        ) : (
          <ul className="problem-rows">
            {problems.map((problem) => (
              <li key={problem.problem_id} className="problem-row" data-testid={`problem-${problem.problem_id}`}>
                <div className="problem-row-text">
                  <strong>{problem.title || problem.problem_id}</strong>
                  <p>{problem.text}</p>
                  <span className="problem-source">
                    {problem.source === "approved" ? "승인 문제" : "직접 등록"}
                    {problem.source_run_id ? ` (${problem.source_run_id})` : ""}
                  </span>
                </div>
                <button
                  type="button"
                  className="button-delete"
                  onClick={() => handleDelete(problem.problem_id)}
                >
                  삭제
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

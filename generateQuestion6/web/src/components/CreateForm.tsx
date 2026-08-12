"use client";

import { useState } from "react";
import Link from "next/link";

import { createGeneration } from "@/lib/api";
import { ProblemPicker } from "./ProblemPicker";

const DIFFICULTIES = ["", "중", "중상", "상"];
const IDEATOR_COUNTS = [1, 2, 3, 4, 5];
const REFINE_COUNTS = [0, 1, 2, 3];

/** 생성 화면 폼 — 원문제 입력(텍스트/라이브러리) + 생성 옵션. */
export function CreateForm({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [mode, setMode] = useState<"text" | "problem">("text");
  const [text, setText] = useState("");
  const [problemId, setProblemId] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [ideatorCount, setIdeatorCount] = useState(3);
  const [maxRefine, setMaxRefine] = useState(2);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    !submitting && (mode === "text" ? text.trim().length > 0 : problemId !== "");

  const handleSubmit = async () => {
    if (!canSubmit) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const source =
        mode === "text"
          ? { mode: "text" as const, text: text.trim() }
          : { mode: "problem" as const, problem_id: problemId };
      const result = await createGeneration(source, {
        difficulty_target: difficulty,
        ideator_count: ideatorCount,
        max_refine: maxRefine,
      });
      onNavigate(`/runs/${result.run_id}/progress`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
      setSubmitting(false);
    }
  };

  return (
    <div className="create-form">
      <fieldset className="create-source">
        <legend>원문제 입력</legend>
        <div className="create-mode-row">
          <label>
            <input type="radio" checked={mode === "text"} onChange={() => setMode("text")} />
            텍스트 붙여넣기
          </label>
          <label>
            <input type="radio" checked={mode === "problem"} onChange={() => setMode("problem")} />
            기존 문제에서 선택
          </label>
        </div>
        {mode === "text" ? (
          <textarea
            aria-label="문제 본문"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="변형할 원문제 본문을 붙여넣으세요"
            rows={8}
          />
        ) : (
          <ProblemPicker value={problemId} onSelect={setProblemId} />
        )}
      </fieldset>

      <fieldset className="create-options">
        <legend>생성 옵션</legend>
        <label>
          난이도 목표
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            {DIFFICULTIES.map((level) => (
              <option key={level || "default"} value={level}>
                {level || "자동"}
              </option>
            ))}
          </select>
        </label>
        <label>
          발상 개수
          <select value={ideatorCount} onChange={(e) => setIdeatorCount(Number(e.target.value))}>
            {IDEATOR_COUNTS.map((count) => (
              <option key={count} value={count}>
                {count}
              </option>
            ))}
          </select>
        </label>
        <label>
          개선 횟수
          <select value={maxRefine} onChange={(e) => setMaxRefine(Number(e.target.value))}>
            {REFINE_COUNTS.map((count) => (
              <option key={count} value={count}>
                {count}
              </option>
            ))}
          </select>
        </label>
      </fieldset>

      {error && <p className="create-error">{error}</p>}

      <div className="create-actions">
        <Link className="create-cancel" href="/">
          취소
        </Link>
        <button
          type="button"
          className="button-create"
          onClick={handleSubmit}
          disabled={!canSubmit}
        >
          {submitting ? "생성 중…" : "생성 시작"}
        </button>
      </div>
    </div>
  );
}

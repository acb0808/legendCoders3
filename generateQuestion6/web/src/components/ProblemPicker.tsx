"use client";

import { useEffect, useMemo, useState } from "react";

import { listProblems } from "@/lib/api";
import type { Problem } from "@/lib/types";

/** 문제 라이브러리 선택 드롭다운 (검색 포함). */
export function ProblemPicker({
  value,
  onSelect,
}: {
  value: string;
  onSelect: (problemId: string) => void;
}) {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listProblems()
      .then((data) => {
        if (!cancelled) {
          setProblems(data);
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : String(reason));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) {
      return problems;
    }
    return problems.filter((p) => `${p.title} ${p.text}`.toLowerCase().includes(keyword));
  }, [problems, query]);

  return (
    <div className="problem-picker">
      {error && <p className="problems-error">{error}</p>}
      <input
        type="search"
        placeholder="문제 검색"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="문제 검색"
      />
      <select
        value={value}
        onChange={(e) => onSelect(e.target.value)}
        aria-label="문제 선택"
        data-testid="problem-select"
      >
        <option value="">문제를 선택하세요</option>
        {filtered.map((problem) => (
          <option key={problem.problem_id} value={problem.problem_id} title={problem.text}>
            {problem.title
              ? `${problem.title} — ${problem.text.slice(0, 40)}`
              : problem.text.slice(0, 40)}
          </option>
        ))}
      </select>
    </div>
  );
}

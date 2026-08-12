"use client";

import { useState } from "react";

import type { ValidationEvidence } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = {
  PASS: "통과",
  FAIL: "실패",
  UNRESOLVED: "판단 불능",
};

/** 검증 증거 패널 — 핵심 PASS·FAIL·UNRESOLVED 상태는 항상 보이고 상세는 접을 수 있다. (T06.4-UT5) */
export function EvidencePanel({ evidence }: { evidence: ValidationEvidence | null | undefined }) {
  const [open, setOpen] = useState(false);
  const checks = evidence?.checks ?? [];

  if (checks.length === 0) {
    return (
      <section aria-label="검증 증거" className="evidence-panel">
        <p className="evidence-empty">검증 증거 없음</p>
      </section>
    );
  }

  const summary = checks.map((check) => ({
    id: check.check_id,
    status: check.status,
    label: STATUS_LABEL[check.status] ?? check.status,
  }));

  return (
    <section aria-label="검증 증거" className="evidence-panel">
      <ul className="evidence-status-list" aria-label="검증 상태 요약">
        {summary.map((entry) => (
          <li key={entry.id} className={`evidence-status evidence-status-${entry.status}`}>
            <span className="evidence-status-badge" data-status={entry.status}>
              {entry.label}
            </span>
            <span className="evidence-status-id">{entry.id}</span>
          </li>
        ))}
      </ul>

      <button
        type="button"
        className="evidence-toggle"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        {open ? "상세 증거 접기" : "상세 증거 보기"}
      </button>

      {open && (
        <div className="evidence-detail">
          {checks.map((check) => (
            <details key={check.check_id} className="evidence-check" open>
              <summary>
                {check.check_id} · {STATUS_LABEL[check.status] ?? check.status}
                {check.critical ? " · 필수" : ""}
              </summary>
              <dl>
                <dt>종류</dt>
                <dd>{check.kind}</dd>
                <dt>근거</dt>
                <dd>
                  <pre>{JSON.stringify(check.evidence ?? {}, null, 2)}</pre>
                </dd>
                {check.counterexample !== null && (
                  <>
                    <dt>반례</dt>
                    <dd>
                      <pre>{JSON.stringify(check.counterexample, null, 2)}</pre>
                    </dd>
                  </>
                )}
                {check.tool_version !== null && (
                  <>
                    <dt>도구 버전</dt>
                    <dd>{check.tool_version}</dd>
                  </>
                )}
              </dl>
            </details>
          ))}
        </div>
      )}
    </section>
  );
}

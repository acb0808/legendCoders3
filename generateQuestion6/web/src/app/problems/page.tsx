import type { Metadata } from "next";
import Link from "next/link";

import { ProblemLibrary } from "@/components/ProblemLibrary";

export const metadata: Metadata = {
  title: "문제 라이브러리",
};

export default function ProblemsPage() {
  return (
    <main className="problems-page">
      <div className="page-frame">
        <header className="problems-header">
          <p className="problems-eyebrow">
            <Link href="/">← 실행 목록</Link>
          </p>
          <h1>문제 라이브러리</h1>
          <p className="problems-sub">
            원문제를 등록하거나, 검토에서 승인된 문제를 확인할 수 있습니다.
          </p>
        </header>
        <ProblemLibrary />
      </div>
    </main>
  );
}

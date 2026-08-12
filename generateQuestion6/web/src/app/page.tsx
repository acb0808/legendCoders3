import Link from "next/link";
import { RunList } from "@/components/RunList";

export default function HomePage() {
  return (
    <main className="home-page">
      <header className="home-header">
        <p className="home-eyebrow">공통수학Ⅱ · 도형의 방정식</p>
        <h1>수학문제 변형·생성기</h1>
        <p className="home-sub">검증된 변형 후보를 교사가 검토하고 승인·반려하는 작업대</p>
        <div className="home-actions">
          <Link className="home-action-primary" href="/create">
            새 문제 만들기
          </Link>
          <Link className="home-action-secondary" href="/problems">
            문제 라이브러리
          </Link>
        </div>
      </header>
      <RunList />
    </main>
  );
}

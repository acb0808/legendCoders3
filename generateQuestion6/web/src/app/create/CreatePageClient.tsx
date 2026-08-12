"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { CreateForm } from "@/components/CreateForm";

/** 새 문제 생성 화면 클라이언트 — 라우팅만 담당한다. */
export function CreatePageClient() {
  const router = useRouter();
  return (
    <>
      <header className="create-header">
        <p className="create-eyebrow">
          <Link href="/">← 실행 목록</Link>
        </p>
        <h1>새 문제 만들기</h1>
        <p className="create-sub">
          원문제를 입력하거나 라이브러리에서 선택하면 다중 에이전트 파이프라인이 새 문항을 제작합니다.
        </p>
      </header>
      <CreateForm onNavigate={(path) => router.push(path)} />
    </>
  );
}

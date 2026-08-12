import type { Metadata } from "next";

import { CreatePageClient } from "./CreatePageClient";

export const metadata: Metadata = {
  title: "새 문제 생성",
};

export default function CreatePage() {
  return (
    <main className="create-page">
      <div className="page-frame">
        <CreatePageClient />
      </div>
    </main>
  );
}

import type { Metadata } from "next";

import { ProgressClient } from "./ProgressClient";

export const metadata: Metadata = {
  title: "생성 진행",
};

export default function RunProgressPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  return (
    <main className="progress-page">
      <div className="page-frame">
        <ProgressClient runIdPromise={params} />
      </div>
    </main>
  );
}

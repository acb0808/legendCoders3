import type { Metadata } from "next";

import { ReviewClient } from "./ReviewClient";

export const metadata: Metadata = {
  title: "후보 비교·검토",
};

export default function RunReviewPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  return (
    <main className="review-page">
      <div className="page-frame">
        <ReviewClient runIdPromise={params} />
      </div>
    </main>
  );
}

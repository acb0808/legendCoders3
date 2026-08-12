import type { Metadata } from "next";
import type { ReactNode } from "react";

import "katex/dist/katex.min.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "수학문제 변형 검토",
  description: "공통수학2 도형의 방정식 서술형 변형 문항 교사 검토 화면",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}

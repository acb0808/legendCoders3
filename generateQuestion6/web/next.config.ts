import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // 127.0.0.1 로 접속해도 HMR websocket 이 차단되지 않도록 허용한다.
  allowedDevOrigins: ["127.0.0.1"],
  // 교사 화면은 백엔드 FastAPI 를 통해서만 데이터를 받는다.
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  },
};

export default nextConfig;

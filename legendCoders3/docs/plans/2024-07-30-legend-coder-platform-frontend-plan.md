# 레전드 코더 플랫폼 프론트엔드 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Next.js, TypeScript, Tailwind CSS를 사용하여 레전드 코더 플랫폼의 웹 인터페이스를 구축합니다.

**Architecture:** Next.js (App Router) 기반의 SPA로, 백엔드 API와 통신하며 JWT를 사용하여 인증을 처리합니다.

**Tech Stack:** Next.js, TypeScript, Tailwind CSS, Lucide React (Icons), Axios/Fetch (API calls).

---

### Task 1: 프론트엔드 프로젝트 초기 설정

**Goal:** Next.js 프로젝트를 생성하고, Tailwind CSS 및 필요한 라이브러리를 설치하며 기본 폴더 구조를 설정합니다.

**Files:**
- Create: `frontend/` (root directory)
- Create: `frontend/package.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx` (Landing Page)

**Step 1: Next.js 프로젝트 생성**

```bash
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*"
```
(모든 옵션은 기본값으로 진행하되, `src` 폴더는 사용하지 않는 방향으로 설정합니다.)

**Step 2: 필요한 추가 라이브러리 설치**

```bash
cd frontend
npm install axios lucide-react clsx tailwind-merge
```

**Step 3: API 클라이언트 설정 (axios)**

`frontend/lib/api.ts`를 생성하여 백엔드 서버 주소 및 토큰 처리를 설정합니다.

**Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: Initial frontend project setup with Next.js and Tailwind"
```

### Task 2: 인증 UI 및 기능 구현 (로그인/회원가입)

**Goal:** 로그인 및 회원가입 페이지를 만들고, JWT 토큰을 로컬 스토리지에 저장하여 인증 상태를 유지하는 기능을 구현합니다.

**Files:**
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/app/register/page.tsx`
- Create: `frontend/components/auth-provider.tsx` (Context for Auth)

**Step 1: 로그인 페이지 UI 구현**

**Step 2: 회원가입 페이지 UI 구현**

**Step 3: 로그인/회원가입 API 연동 및 토큰 저장 로직**

**Step 4: Commit**

```bash
git add ...
git commit -m "feat: Implement Login and Register pages with JWT handling"
```

### Task 3: 메인 대시보드 및 네비게이션 구현

**Goal:** 상단 네비게이션 바와 사용자의 통계(해결 문제 수, 스트릭)를 보여주는 메인 대시보드를 구현합니다.

**Files:**
- Create: `frontend/components/navbar.tsx`
- Create: `frontend/app/dashboard/page.tsx`
- Create: `frontend/components/stats-card.tsx`

**Step 1: 공통 네비게이션 바 구현**

**Step 2: 대시보드 레이아웃 및 통계 데이터 연동 (`GET /stats/me`)**

**Step 3: Commit**

```bash
git add ...
git commit -m "feat: Implement dashboard and navigation bar"
```

### Task 4: 오늘의 문제 및 제출 기능 구현

**Goal:** 오늘의 문제 정보를 표시하고, 사용자가 백준 제출 결과를 등록할 수 있는 화면을 구현합니다.

**Files:**
- Create: `frontend/app/problems/today/page.tsx`
- Create: `frontend/components/problem-detail.tsx`
- Create: `frontend/components/submission-form.tsx`

**Step 1: 오늘의 문제 조회 API 연동 (`GET /daily-problems/today`)**

**Step 2: 문제 정보 및 백준 링크 표시**

**Step 3: 제출 결과 등록 폼 및 API 연동 (`POST /submissions/register`)**

**Step 4: Commit**

```bash
git add ...
git commit -m "feat: Implement daily problem view and submission registration"
```

### Task 5: 랭킹 및 커뮤니티 페이지 구현

**Goal:** 전체 사용자 랭킹 페이지와 문제별 게시판/댓글 기능을 구현합니다.

**Files:**
- Create: `frontend/app/ranking/page.tsx`
- Create: `frontend/app/problems/[id]/posts/page.tsx`
- Create: `frontend/components/comment-section.tsx`

**Step 1: 랭킹 페이지 구현 (`GET /stats/ranking`)**

**Step 2: 문제별 게시글 목록 및 작성 기능**

**Step 3: 게시글 상세 및 댓글 시스템**

**Step 4: Commit**

```bash
git add ...
git commit -m "feat: Implement ranking and community features"
```

# 레전드 코더 플랫폼 기획 문서 및 기능 명세서

## 1. 프로젝트 개요

레전드 코더 플랫폼은 알고리즘 학습 및 코딩 테스트 준비를 위한 커뮤니티 기반 웹 서비스입니다. 매일 AI가 선정한 백준 문제를 풀고, 해결 과정을 공유하며, 다른 사용자들과 토론하고, 개인의 학습 진행 상황을 체계적으로 관리할 수 있는 환경을 제공합니다. 기존 오프라인 스터디의 장점을 온라인으로 확장하여 더 많은 사용자가 참여하고 성장할 수 있도록 돕는 것을 목표로 합니다.

## 2. 프로젝트 목표

*   **참여 증대:** 더 많은 사용자가 매일 백준 문제 풀이에 참여하고 알고리즘 실력을 향상시키도록 유도합니다.
*   **커뮤니티 활성화:** 문제 풀이 과정과 아이디어를 공유하고, 토론하며, 서로에게 힌트를 제공하는 활발한 커뮤니티를 구축합니다.
*   **체계적인 학습 관리:** 개인의 문제 해결 기록, 랭킹, 성취도를 시각적으로 제공하여 학습 동기를 부여하고 성취감을 느끼게 합니다.
*   **종합 학습 도구:** 장기적으로 코딩 테스트 준비를 위한 포괄적인 학습 플랫폼으로 발전시킵니다.

## 3. 대상 사용자

*   **중급 개발자:** 특정 알고리즘 유형에 대한 이해를 심화하고 코딩 테스트 실력을 향상시키고자 하는 개발자.
*   **고급 개발자:** 고난도 문제 해결을 즐기며, 새로운 문제 해결 전략을 탐구하고 다른 개발자들과 지식을 공유하고자 하는 개발자.
*   **초보자 포함:** 장기적으로는 초보자도 쉽게 접근하여 점진적으로 실력을 키울 수 있는 환경을 제공합니다.

## 4. 핵심 가치 제안

*   **AI 기반의 맞춤형 문제 추천 (테마 기반):** 매일 12시, AI가 난이도와 테마를 고려한 문제를 제시하여 학습의 연속성과 흥미를 유지합니다.
*   **활발한 학습 커뮤니티:** 문제 풀이 후 코드와 아이디어를 공유하고 토론하며, 질의응답을 통해 함께 성장하는 환경을 제공합니다.
*   **동기 부여 및 성취감:** 개인 및 팀 랭킹, 성취도 시스템을 통해 학습 목표를 설정하고 달성하는 재미를 선사합니다.
*   **백준 연동을 통한 편리한 경험:** 백준과의 간접적인 연동(사용자가 백준에 직접 제출 후 결과 크롤링)을 통해 학습 흐름이 끊기지 않습니다.

## 5. 고수준 아키텍처

레전드 코더 플랫폼은 모듈식 API 기반 아키텍처를 채택하여 프론트엔드와 백엔드를 분리합니다.

*   **프론트엔드 (사용자 인터페이스):** React.js(Next.js 포함 가능) 기반의 SPA로 사용자 경험 및 인터페이스를 담당합니다.
*   **백엔드 (API 서버):** Python FastAPI 기반으로 모든 비즈니스 로직(사용자 관리, 백준 연동, AI 문제 선정, 데이터 처리 등)을 처리하고 프론트엔드에 API를 제공합니다.
*   **데이터베이스:** PostgreSQL을 사용하여 사용자 데이터, 문제 정보, 게시물, 랭킹 등 모든 영구 데이터를 저장합니다.
*   **외부 서비스 연동:** 사용자가 백준에 직접 문제를 해결하고 제출한 후, 백엔드가 백준 웹사이트를 크롤링하여 제출 결과(상태, 시간, 메모리 등)를 가져옵니다.
*   **AI 문제 선택기 모듈:** 백엔드 내에 구현되어 매일 문제를 선정하는 AI 로직을 담당합니다.

## 6. 기술 스택 (Technology Stack)

*   **프론트엔드:** React.js (TypeScript), Next.js (선택 사항), Tailwind CSS.
*   **백엔드:** Python, FastAPI. 웹 크롤링을 위해 `BeautifulSoup`, `requests` 또는 `Selenium`과 같은 Python 라이브러리 활용.
*   **데이터베이스:** PostgreSQL.
*   **AI 문제 선정:** Python 기반 라이브러리 활용 (Pandas, scikit-learn 등).
*   **배포:** Vercel (프론트엔드), AWS/GCP/DigitalOcean (백엔드, DB).

---

## 7. 기능 명세서 (Functional Specification Document)

### 7.1. 사용자 관리 및 인증 (User Management & Authentication)

*   **7.1.1. 회원가입 (Registration)**
    *   **설명:** 새로운 사용자가 플랫폼에 가입합니다.
    *   **사용자 흐름:**
        1.  사용자가 회원가입 페이지에 접속합니다.
        2.  이메일, 비밀번호, 닉네임, **필수적으로 백준 ID**를 입력하고 '가입하기' 버튼을 클릭합니다.
        3.  입력 값 유효성 검증을 수행합니다.
        4.  성공 시 회원가입 완료 페이지로 이동하거나 로그인 상태로 전환됩니다.
        5.  실패 시 오류 메시지를 표시합니다.
    *   **데이터 모델 (User):**
        *   `id` (UUID): 사용자 고유 식별자
        *   `email` (String): 사용자 이메일 (로그인 ID)
        *   `password_hash` (String): 비밀번호 해시 값
        *   `nickname` (String): 사용자 닉네임 (고유)
        *   `baekjoon_id` (String): 연동된 백준 ID (필수)
        *   `created_at` (DateTime): 생성일
        *   `updated_at` (DateTime): 최종 수정일
    *   **API 엔드포인트:**
        *   `POST /api/auth/register` (이메일, 비밀번호, 닉네임, 백준 ID)

*   **7.1.2. 로그인 (Login)**
    *   **설명:** 등록된 사용자가 플랫폼에 로그인합니다.
    *   **사용자 흐름:**
        1.  사용자가 로그인 페이지에 접속합니다.
        2.  이메일과 비밀번호를 입력하고 '로그인' 버튼을 클릭합니다.
        3.  인증 성공 시 메인 페이지로 리다이렉트되고 인증 토큰을 발급받습니다.
        4.  실패 시 오류 메시지를 표시합니다.
    *   **API 엔드포인트:**
        *   `POST /api/auth/login` (이메일, 비밀번호) -> 토큰 반환

*   **7.1.3. 사용자 프로필 (User Profile)**
    *   **설명:** 사용자의 개인 정보, 문제 해결 통계, 랭킹 정보 등을 표시합니다.
    *   **사용자 흐름:**
        1.  사용자가 자신의 프로필 페이지에 접속합니다.
        2.  닉네임, 백준 ID, 해결한 문제 수, 랭킹, 성취도 등의 정보를 조회합니다.
        3.  프로필 정보 (닉네임, 백준 ID 등)를 수정할 수 있습니다.
        4.  백준 ID는 사용자가 백준에 제출한 기록을 크롤링하기 위한 필수 정보입니다.
    *   **API 엔드포인트:**
        *   `GET /api/users/{user_id}` (사용자 정보 조회)
        *   `PUT /api/users/{user_id}` (사용자 정보 수정)

### 7.2. 매일 문제 챌린지 (Daily Problem Challenge)

*   **7.2.1. AI 기반 문제 선정 (AI-driven Problem Selection)**
    *   **설명:** 매일 12시 KST에 AI 모듈이 다음날의 백준 문제를 선정합니다.
    *   **동작 방식:**
        1.  백엔드의 스케줄러가 매일 12시에 AI 문제 선택기 모듈을 트리거합니다.
        2.  AI 모듈은 다음 기준을 바탕으로 문제 데이터베이스에서 적절한 백준 문제 ID를 선정합니다.
            *   난이도 (티어): 주로 중급~고급 문제 위주.
            *   알고리즘 유형: 주간/월간 테마에 맞는 유형 우선 선정.
            *   이전 출제 이력: 최근에 출제되지 않은 문제 우선.
            *   사용자 반응 (장기적으로): 문제 해결률, 토론 참여도 등.
        3.  선정된 문제 ID는 `DailyProblem` 테이블에 저장됩니다.
    *   **데이터 모델 (DailyProblem):**
        *   `id` (UUID): 고유 식별자
        *   `problem_date` (Date): 문제 출제 날짜
        *   `baekjoon_problem_id` (Integer): 백준 문제 ID
        *   `title` (String): 문제 제목
        *   `description` (Text): 문제 설명 (HTML 또는 Markdown)
        *   `input_example` (Text): 입력 예시
        *   `output_example` (Text): 출력 예시
        *   `time_limit_ms` (Integer): 시간 제한 (밀리초)
        *   `memory_limit_mb` (Integer): 메모리 제한 (메가바이트)
        *   `difficulty_level` (String): 난이도 (예: Silver I, Gold II 등)
        *   `algorithm_type` (String, Array): 알고리즘 유형 (예: DP, Graph, BFS 등)
        *   `created_at` (DateTime): 생성일

*   **7.2.2. 오늘의 문제 조회 (View Daily Problem)**
    *   **설명:** 사용자는 오늘의 문제를 확인하고 문제 상세 정보를 조회합니다.
    *   **사용자 흐름:**
        1.  사용자가 메인 페이지 또는 오늘의 문제 페이지에 접속합니다.
        2.  AI가 선정한 오늘의 문제 상세 정보(제목, 설명, 예시, 제한 조건, 백준 원본 링크)를 조회합니다.
        3.  백준 원본 링크를 통해 백준 사이트로 이동할 수 있습니다.
    *   **API 엔드포인트:**
        *   `GET /api/daily-problems/today` (오늘의 문제 조회)
        *   `GET /api/daily-problems/{date}` (특정 날짜 문제 조회)

*   **7.2.3. 제출 결과 등록 및 채점 (Register Submission Result & Judging)**
    *   **설명:** 사용자는 백준에 직접 코드를 제출하고, 플랫폼에서는 해당 제출 결과(Baekjoon Submission ID)를 등록하여 채점 내용을 크롤링하여 가져옵니다.
    *   **사용자 흐름:**
        1.  사용자는 오늘의 문제를 백준 웹사이트에서 직접 풉니다.
        2.  사용자가 백준 웹사이트에 직접 코드를 제출하여 채점을 받습니다.
        3.  플랫폼의 '제출 결과 등록' 페이지 또는 기능에서, 사용자는 백준에서 제출한 **제출 ID (Submission ID)**를 입력합니다.
        4.  백엔드는 사용자로부터 받은 제출 ID와 백준 ID (`User` 모델에 저장된)를 이용하여 **백준 웹사이트에서 해당 제출 결과 페이지를 크롤링합니다.**
        5.  크롤링된 데이터를 파싱하여 채점 결과(Accepted, Wrong Answer, Time Limit Exceeded 등), 런타임, 메모리 사용량 등을 추출합니다.
        6.  추출된 정보와 사용자의 백준 제출 코드를 `Submission` 테이블에 저장합니다. (필요 시 백준에서 코드 내용도 크롤링)
        7.  사용자에게 채점 결과가 성공적으로 등록되었음을 알립니다.
    *   **데이터 모델 (Submission):**
        *   `id` (UUID): 제출 고유 식별자
        *   `user_id` (UUID): 사용자 ID (Foreign Key)
        *   `daily_problem_id` (UUID): 해당 일일 문제 ID (Foreign Key)
        *   `baekjoon_problem_id` (Integer): 백준 문제 ID
        *   `baekjoon_submission_id` (Integer): 백준 사이트의 제출 ID
        *   `language` (String): 사용 언어 (예: Python, Java, C++)
        *   `code` (Text, Optional): 제출된 코드 내용 (크롤링 또는 사용자가 직접 입력)
        *   `status` (Enum): 채점 상태 (예: Accepted, Wrong Answer, Time Limit Exceeded, Runtime Error 등)
        *   `result_message` (String, Optional): 채점 결과 메시지
        *   `runtime_ms` (Integer, Optional): 실행 시간 (밀리초)
        *   `memory_usage_kb` (Integer): 메모리 사용량 (킬로바이트)
        *   `submitted_at` (DateTime): 제출 시각 (백준 제출 시각 또는 플랫폼 등록 시각)
    *   **API 엔드포인트:**
        *   `POST /api/submissions/register` (백준 제출 ID를 받아 결과 등록)
        *   `GET /api/submissions/{submission_id}` (등록된 제출 결과 조회)

*   **7.2.4. 제출 기록 조회 (View Submission History)**
    *   **설명:** 사용자는 각 문제에 대해 자신이 제출했던 코드와 채점 기록을 확인할 수 있습니다.
    *   **사용자 흐름:**
        1.  사용자가 특정 문제 페이지 또는 자신의 프로필 페이지에서 제출 기록 섹션에 접속합니다.
        2.  제출 기록 목록 (제출 시각, 언어, 결과, 실행 시간, 메모리 등)을 조회합니다.
        3.  각 제출 기록을 클릭하여 제출했던 코드 내용을 확인할 수 있습니다.
    *   **API 엔드포인트:**
        *   `GET /api/daily-problems/{daily_problem_id}/submissions` (특정 문제의 내 제출 기록 조회)

### 7.3. 커뮤니티 및 토론 (Community & Discussion)

*   **7.3.1. 문제별 토론 게시판 (Problem-specific Discussion Forum)**
    *   **설명:** 각 일일 문제마다 사용자들의 풀이 과정, 아이디어 공유, 질문/답변, 힌트 교환을 위한 전용 토론 게시판을 제공합니다.
    *   **사용자 흐름:**
        1.  사용자가 특정 일일 문제 페이지에 접속하면 해당 문제의 토론 게시판을 볼 수 있습니다.
        2.  사용자는 새 토론 글을 작성하거나 기존 토론 글에 댓글을 달 수 있습니다.
        3.  글 작성 시 제목, 내용(코드, 이미지 포함 가능), 태그 등을 입력할 수 있습니다.
        4.  다른 사용자의 글에 '좋아요' 또는 '비추천'을 할 수 있습니다 (선택 사항).
        5.  자신이 작성한 글 또는 댓글을 수정/삭제할 수 있습니다.
        6.  글 목록에서 인기순, 최신순 등으로 정렬하여 볼 수 있습니다.
    *   **데이터 모델 (Post):**
        *   `id` (UUID): 게시글 고유 식별자
        *   `user_id` (UUID): 작성자 ID (Foreign Key)
        *   `daily_problem_id` (UUID): 관련 일일 문제 ID (Foreign Key)
        *   `title` (String): 게시글 제목
        *   `content` (Text): 게시글 내용 (마크다운 지원)
        *   `tags` (String Array, Optional): 관련 태그 (예: #BFS, #DP, #Python)
        *   `view_count` (Integer): 조회수
        *   `like_count` (Integer): 좋아요 수
        *   `created_at` (DateTime): 생성일
        *   `updated_at` (DateTime): 최종 수정일
    *   **API 엔드포인트:**
        *   `GET /api/daily-problems/{daily_problem_id}/posts` (특정 문제의 게시글 목록 조회)
        *   `GET /api/posts/{post_id}` (게시글 상세 조회)
        *   `POST /api/daily-problems/{daily_problem_id}/posts` (새 게시글 작성)
        *   `PUT /api/posts/{post_id}` (게시글 수정)
        *   `DELETE /api/posts/{post_id}` (게시글 삭제)
        *   `POST /api/posts/{post_id}/like` (게시글 좋아요/취소)

*   **7.3.2. 댓글 및 답글 시스템 (Comment & Reply System)**
    *   **설명:** 게시글 아래에 댓글을 달고, 댓글에 답글을 달아 계층적인 토론을 가능하게 합니다.
    *   **사용자 흐름:**
        1.  게시글 상세 페이지에서 댓글 목록을 조회합니다.
        2.  사용자는 특정 게시글에 댓글을 작성하거나, 기존 댓글에 답글을 작성할 수 있습니다.
        3.  자신이 작성한 댓글/답글을 수정/삭제할 수 있습니다.
        4.  다른 사용자의 댓글/답글에 '좋아요'를 할 수 있습니다 (선택 사항).
    *   **데이터 모델 (Comment):**
        *   `id` (UUID): 댓글 고유 식별자
        *   `user_id` (UUID): 작성자 ID (Foreign Key)
        *   `post_id` (UUID): 관련 게시글 ID (Foreign Key)
        *   `parent_comment_id` (UUID, Optional): 답글인 경우 부모 댓글 ID (Foreign Key)
        *   `content` (Text): 댓글 내용
        *   `like_count` (Integer): 좋아요 수
        *   `created_at` (DateTime): 생성일
        *   `updated_at` (DateTime): 최종 수정일
    *   **API 엔드포인트:**
        *   `GET /api/posts/{post_id}/comments` (게시글의 댓글 목록 조회)
        *   `POST /api/posts/{post_id}/comments` (새 댓글 작성)
        *   `POST /api/comments/{comment_id}/reply` (댓글에 답글 작성)
        *   `PUT /api/comments/{comment_id}` (댓글 수정)
        *   `DELETE /api/comments/{comment_id}` (댓글 삭제)
        *   `POST /api/comments/{comment_id}/like` (댓글 좋아요/취소)

### 7.4. 랭킹 및 성과 관리 (Ranking & Achievement Management)

*   **7.4.1. 개인 랭킹 (Individual Ranking)**
    *   **설명:** 사용자들의 문제 해결 성과를 바탕으로 순위를 매겨 경쟁을 유도하고 동기를 부여합니다.
    *   **사용자 흐름:**
        1.  사용자가 랭킹 페이지에 접속합니다.
        2.  전체 사용자 또는 특정 기간(예: 주간, 월간)별 랭킹을 조회합니다.
        3.  랭킹 기준은 다음과 같습니다:
            *   **해결한 문제 수 (Total Solved Count):** 가장 기본적인 랭킹 기준.
            *   **연속 해결 일수 (Consecutive Solve Days):** 꾸준한 참여를 장려.
            *   **평균 해결 시간 (Average Solve Time):** 효율적인 문제 해결 능력 반영.
            *   **난이도별 해결 점수 (Difficulty-based Score):** 난이도가 높은 문제 해결 시 더 높은 점수 부여.
        4.  자신의 랭킹과 상위 랭커들의 정보를 확인할 수 있습니다.
    *   **데이터 모델 (UserStats - `User` 모델에 통합되거나 별도 테이블):**
        *   `user_id` (UUID): 사용자 ID (Foreign Key)
        *   `total_solved_count` (Integer): 총 해결 문제 수
        *   `current_consecutive_days` (Integer): 현재 연속 해결 일수
        *   `max_consecutive_days` (Integer): 최대 연속 해결 일수
        *   `total_solve_time_ms` (BigInteger): 총 문제 해결 시간 (밀리초)
        *   `average_solve_time_ms` (Integer): 평균 문제 해결 시간 (밀리초)
        *   `difficulty_score` (Integer): 난이도 기반 점수
        *   `last_solved_date` (Date): 마지막으로 문제를 해결한 날짜
        *   `updated_at` (DateTime): 최종 갱신일
    *   **API 엔드포인트:**
        *   `GET /api/ranking/total-solved` (총 해결 문제 수 랭킹 조회)
        *   `GET /api/ranking/consecutive-days` (연속 해결 일수 랭킹 조회)
        *   `GET /api/ranking/average-time` (평균 해결 시간 랭킹 조회)
        *   `GET /api/ranking/difficulty-score` (난이도 점수 랭킹 조회)

*   **7.4.2. 성과/도전 과제 시스템 (Achievement/Challenge System)**
    *   **설명:** 특정 목표 달성 시 사용자에게 배지나 포인트를 부여하여 성취감을 제공하고 지속적인 참여를 독려합니다.
    *   **사용자 흐름:**
        1.  사용자가 성과/도전 과제 페이지에서 달성 가능한 과제 목록과 자신의 달성 현황을 조회합니다.
        2.  달성한 과제에 대한 배지 또는 설명을 확인할 수 있습니다.
        3.  달성한 성과는 프로필 페이지에 표시될 수 있습니다.
    *   **데이터 모델 (Achievement):**
        *   `id` (UUID): 성과 고유 식별자
        *   `name` (String): 성과 이름 (예: "첫 발자국", "7일 연속 해결")
        *   `description` (Text): 성과 설명
        *   `criteria` (JSON): 성과 달성 조건 (예: `{"type": "solved_count", "value": 1}`)
        *   `icon_url` (String, Optional): 성과 아이콘 이미지 URL
    *   **데이터 모델 (UserAchievement):**
        *   `user_id` (UUID): 사용자 ID (Foreign Key)
        *   `achievement_id` (UUID): 달성한 성과 ID (Foreign Key)
        *   `achieved_at` (DateTime): 달성 시각
    *   **API 엔드포인트:**
        *   `GET /api/achievements` (전체 성과 목록 조회)
        *   `GET /api/users/{user_id}/achievements` (특정 사용자의 달성 성과 목록 조회)

*   **7.4.3. 학습 진행 상황 시각화 (Learning Progress Visualization)**
    *   **설명:** 사용자가 자신의 학습 진행 상황을 한눈에 파악할 수 있도록 시각적인 데이터를 제공합니다.
    *   **사용자 흐름:**
        1.  사용자가 프로필 페이지 또는 대시보드에서 자신의 학습 진행 상황을 조회합니다.
        2.  제공되는 시각화 자료:
            *   **해결 문제 달력:** 백준 잔디밭처럼 문제를 해결한 날짜를 표시.
            *   **난이도별 해결 현황 그래프:** 난이도(티어)별 해결한 문제 수 비율.
            *   **알고리즘 유형별 해결 현황 그래프:** DP, BFS, DFS 등 알고리즘 유형별 해결한 문제 수.
            *   **시간 경과에 따른 문제 해결 트렌드:** 주간/월간 문제 해결 수 변화.
    *   **API 엔드포인트:**
        *   `GET /api/users/{user_id}/progress/calendar` (해결 문제 달력 데이터)
        *   `GET /api/users/{user_id}/progress/difficulty-stats` (난이도별 통계)
        *   `GET /api/users/{user_id}/progress/algorithm-stats` (알고리즘 유형별 통계)
        *   `GET /api/users/{user_id}/progress/trend` (문제 해결 트렌드 데이터)

### 7.5. 관리자 기능 (Administrator Features)

*   **7.5.1. 사용자 관리 (User Management)**
    *   **설명:** 플랫폼 관리자가 사용자 계정을 관리하고 필요에 따라 조치(예: 계정 비활성화, 정보 수정)를 취할 수 있습니다.
    *   **관리자 흐름:**
        1.  관리자 페이지에서 전체 사용자 목록을 조회합니다.
        2.  특정 사용자를 검색하고 프로필 정보를 열람합니다.
        3.  사용자 계정 활성/비활성화, 닉네임, 백준 ID 등 프로필 정보 수정.
        4.  사용자 역할(일반 사용자, 관리자) 변경 (향후 확장 시).
    *   **API 엔드포인트 (관리자 권한 필요):**
        *   `GET /api/admin/users` (사용자 목록 조회)
        *   `GET /api/admin/users/{user_id}` (특정 사용자 상세 조회)
        *   `PUT /api/admin/users/{user_id}` (사용자 정보 수정)
        *   `PUT /api/admin/users/{user_id}/status` (사용자 계정 상태 변경)

*   **7.5.2. 콘텐츠 관리 (Content Management)**
    *   **설명:** 관리자가 플랫폼 내의 콘텐츠(토론 게시글, 댓글, 성과)를 검토하고 부적절한 콘텐츠를 처리할 수 있습니다.
    *   **관리자 흐름:**
        1.  관리자 페이지에서 게시글, 댓글 등 콘텐츠 목록을 조회합니다.
        2.  부적절한 콘텐츠를 삭제하거나 숨김 처리합니다.
        3.  게시글 내용 수정 (필요 시).
        4.  신고된 콘텐츠 목록을 검토하고 조치합니다.
    *   **API 엔드포인트 (관리자 권한 필요):**
        *   `GET /api/admin/posts` (모든 게시글 목록 조회)
        *   `DELETE /api/admin/posts/{post_id}` (게시글 삭제)
        *   `PUT /api/admin/posts/{post_id}/status` (게시글 상태 변경 - 숨김/공개)
        *   `GET /api/admin/comments` (모든 댓글 목록 조회)
        *   `DELETE /api/admin/comments/{comment_id}` (댓글 삭제)

*   **7.5.3. AI 문제 선정 관리 (AI Problem Selection Management)**
    *   **설명:** 관리자가 AI 문제 선정 로직을 조정하거나, 필요에 따라 수동으로 일일 문제를 재정의할 수 있습니다.
    *   **관리자 흐름:**
        1.  관리자 페이지에서 AI 문제 선정 기록 및 다음 문제 선정 예정 정보를 확인합니다.
        2.  주간/월간 알고리즘 테마를 설정하거나 수정합니다.
        3.  특정 날짜의 문제 선정이 적절하지 않을 경우, 수동으로 다른 백준 문제를 지정하여 대체할 수 있습니다.
        4.  AI 문제 선택기 모듈의 파라미터(예: 난이도 범위)를 조정할 수 있습니다.
    *   **API 엔드포인트 (관리자 권한 필요):**
        *   `GET /api/admin/daily-problems/selection-logs` (AI 문제 선정 로그 조회)
        *   `POST /api/admin/daily-problems/override/{date}` (특정 날짜 문제 수동 재정의)
        *   `PUT /api/admin/settings/algorithm-theme` (알고리즘 테마 설정/수정)
        *   `PUT /api/admin/settings/ai-selector-params` (AI 선택기 파라미터 조정)
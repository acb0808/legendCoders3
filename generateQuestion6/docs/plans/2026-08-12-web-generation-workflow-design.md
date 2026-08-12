# 웹 생성 워크플로 설계 — 문제 기반 새 문제 제작

> 상태: 사용자 승인 완료 (2026-08-12). 섹션 1~6 전부 승인.
> 다음 단계: writing-plans 로 구현 계획 수립.

## 목표

웹에서 사용자가 "가지고 있는 문제"를 입력·선택하면 실제 LLM 다중 에이전트 파이프라인을 실행해
새로운 문제를 생성하고, 단계별 진행 상황과 "어떤 LLM이 호출되어 어떤 결과를 주는지"를 실시간으로
보여주며, 승인된 문제는 라이브러리에 보관·재사용할 수 있게 한다.

## 확정 요구사항 (사용자 결정)

1. **원문제 입력**: 텍스트 붙여넣기 + 기존 문제 라이브러리에서 선택
2. **실행**: 실제 LLM 다중 에이전트 파이프라인 (비동기, 수 분 소요, API 키·비용 발생)
3. **진행 표시**: 단계별 실시간 진행 (SSE) + LLM 호출 상세(호출된 LLM·결과 요약·지연·비용)
4. **옵션**: 난이도 목표·발상 개수·개선 횟수 조절 가능
5. **승인 처리**: 승인된 문제는 보관·재사용 가능한 라이브러리로

## 접근 방식

**A. 기존 FastAPI 앱 확장** (채택) — `src/math_variant/api/`에 생성 작업 + SSE + 문제 라이브러리
엔드포인트 추가, `AgentPipeline`·`StructuredOutputEngine`에 선택적 이벤트 콜백 추가,
Next.js 에 생성/진행/라이브러리 화면 추가. CLI 의 파이프라인 배선을 그대로 재사용.

---

## 섹션 1: 진행 이벤트 모델 + 파이프라인 콜백

### PipelineEvent (api/events.py)

```python
class EventStage(StrEnum):
    PLANNER     # 기획
    IDEATION    # 발상 (배치)
    SELECTION   # 선별
    GENERATION  # 후보별 생성
    CODE_REVIEW # 후보별 스크립트 심사
    SANDBOX     # 후보별 검증 실행
    BLIND       # 후보별 블라인드 합의
    CRITIC      # 후보별 비평
    JUDGE       # 집계
    DONE        # 완료
```

### LLM 호출 이벤트 (엔진 수준, generate_structured 1회당 1건)

```json
{
  "event_id": "evt-001",
  "type": "llm_call",
  "stage": "ideation",
  "request_id": "ideator-0",
  "role": "ideator",
  "schema": "IdeationOutput",
  "provider": "deepseek",
  "model": "deepseek-v4-flash",
  "temperature": 1.4,
  "status": "ok",
  "attempts": 1,
  "latency_ms": 4231,
  "cost_usd": 0.0021,
  "summary": {"idea_id": "idea-0", "title": "질문 역전"},
  "error": null
}
```

- `summary` 는 스키마별 핵심 필드만 추출 (IdeationOutput→제목/차원, GeneratorOutput→주장 답,
  JudgeOutput→랭킹 등)
- 실패 시 `status=error` + `error.code`(SCHEMA_VALIDATION 등) + 복구/폴백 정보
- `StructuredOutputEngine` 에 선택적 `on_event` 콜백 추가 (기본 `None` → CLI·기존 테스트 무영향)
- `AgentPipeline` 에 선택적 `on_event` 콜백 추가 (단계 이벤트 방출, 기본 `None`)

---

## 섹션 2: 백엔드 API + 작업(Job) 실행 모델

### 실행 흐름

```
POST /api/generations
   ├─ payload: { source: {mode:"text", text} | {mode:"problem", problem_id},
   │            options: { difficulty_target?, ideator_count?, max_refine? } }
   ├─ JobStore 에 job 생성 (job_id, status=queued, events=[])
   ├─ background thread 로 파이프라인 실행 (CLI run_pipeline 배선 재사용)
   └─ 응답: { job_id, run_id, status }
```

- 실행은 백그라운드 스레드(`ThreadPoolExecutor` 또는 `asyncio.to_thread`)
- 완료 시 `PipelineReport` → `runs/<run_id>.json` (RunStore 형식) 변환 저장
- 진행 이벤트는 Job 이벤트 로그에 append + SSE 스트리밍

### 엔드포인트

| 메서드 | 경로 | 용도 |
|---|---|---|
| POST | `/api/generations` | 생성 작업 시작 |
| GET | `/api/generations/{job_id}` | 작업 상태 + 누적 이벤트 + 결과 |
| GET | `/api/generations/{job_id}/events` | SSE 스트리밍 (과거 재전송 후 실시간) |
| GET | `/api/problems` | 문제 라이브러리 목록 |
| POST | `/api/problems` | 문제 등록 (텍스트 + 메타데이터) |
| DELETE | `/api/problems/{problem_id}` | 문제 삭제 |
| GET | `/api/approved` | 승인된 문제 목록 |

기존 검토 엔드포인트(`GET /api/runs`, `GET /api/runs/{id}`, `POST .../decision`) 유지.

### 동시성·오류 처리

- 동시 실행 제한: 최대 1개 (Docker 샌드박스·API 키 가정). 실행 중이면 `409`
- 실패 시 job `status=failed` + `error` 이벤트, SSE 전송
- job 상태는 JSON 파일로 영속화, 재시작 시 `running` → `failed`(중단) 처리
- 파이프라인 결과 → RunStore 형식 변환 어댑터:
  - `verification_status`: `test_outcome.passes` → `PASS`, 그 외 기존 로직
  - `test_outcome` → `validation_ref`, 블라인드/비평/코드리뷰 → 요약 메타데이터
  - `public_run()` 의 "PASS 후보만 노출" 정책 유지 → 기존 검토 화면 재사용

---

## 섹션 3: 문제 라이브러리 + 승인 문제 재사용

```python
class Problem(BaseModel):
    problem_id: str
    title: str = ""
    text: str
    source: Literal["manual", "approved"]
    source_run_id: str | None = None
    created_at: datetime
```

- 저장: `data/problems/*.json`
- `POST /api/problems` → 텍스트 붙여넣기 등록
- 검토에서 후보 `approved` 시 자동으로 라이브러리 등록 (`source="approved"`, `source_run_id` 태그)
- `GET /api/approved` = 라이브러리 중 `source="approved"` 필터
- 중복 방지: 정규화 텍스트 sha256 키로 판정, 중복 시 기존 `problem_id` 반환 (멱등)

---

## 섹션 4: 프론트엔드 화면 구조 (Next.js)

| 경로 | 용도 | 상태 |
|---|---|---|
| `/` (기존) | 실행 목록 + "새 문제 만들기" 버튼 | 수정 |
| `/create` | 생성 화면 (텍스트 OR 기존 문제 선택 + 옵션) | 신규 |
| `/runs/{runId}/progress` | 실시간 진행 + LLM 호출 로그 (SSE) | 신규 |
| `/runs/{runId}/review` (기존) | 후보 검토·승인/반려 | 재사용 |
| `/problems` | 문제 라이브러리 관리 | 신규 |

### /create

```
[원문제 입력]
  ( 라디오 ) ● 텍스트 붙여넣기  ○ 기존 문제에서 선택
  [textarea]                        [드롭다운: 라이브러리 목록]
[생성 옵션]
  난이도 목표: (중 / 중상 / 상)
  발상 개수:   (1-5, 기본 3)
  개선 횟수:   (0-3, 기본 2)
[생성 시작] → POST /api/generations → /runs/{runId}/progress
```

### /runs/{runId}/progress

- `EventSource("/api/generations/{job_id}/events")`
- 왼쪽: 단계 체크리스트 (☑ 기획 → 발상 → 선별 → 후보별 → 집계)
- 오른쪽: LLM 호출 로그 (provider/model/결과 요약/지연/비용) — 자동 스크롤
- 완료 시 "검토 화면으로 이동" 버튼, 에러 시 에러 배너 + 재시도

### 신규 컴포넌트

- `CreateForm.tsx`, `ProblemPicker.tsx`, `ProgressView.tsx`, `CallLog.tsx`, `ProblemLibrary.tsx`
- `types.ts` 확장: `Problem`, `GenerationJob`, `JobEvent`, `CreateOptions`
- `api.ts` 확장: `createGeneration`, `getJob`, `streamJobEvents`, `listProblems`,
  `registerProblem`, `deleteProblem`, `listApproved`
- 기존 `CandidateCard`, `CandidateList`, `ReviewActions`, `EvidencePanel`, `RubricView` 재사용

---

## 섹션 5: 테스트 + 품질 게이트

### 백엔드 (pytest)

- JobStore 이벤트 로그·상태 전이(queued→running→completed/failed), SSE 재연결 재전송,
  재시작 running→failed
- AgentPipeline `on_event` → 단계 이벤트 순서·스테이지 (fake 엔진, 실제 LLM 없이)
- StructuredOutputEngine 이벤트 → provider/model/status/error 정확성, `on_event=None` 시 무영향
- API: `POST /api/generations`(동시 409, 옵션 검증), 문제 CRUD 멱등성, 승인 자동 등록
- 어댑터: PipelineReport → RunStore 형식 변환, PASS 후보만 노출 정책 유지
- SSE 엔드포인트: 테스트 클라이언트로 스트림 수신

### 프론트엔드 (vitest, 기존 4개 유지)

- CreateForm 옵션 검증·제출, ProblemPicker 검색·선택, ProgressView SSE→체크리스트·로그 갱신,
  CallLog 렌더링, SSE 에러/재연결, job failed 배너

### 수동 확인

- `math-variant gate` 통과, web `npm test`/`lint`/`typecheck` 통과
- 실제 LLM 파이프라인(유료) 로컬 실전은 사용자 확인

---

## 파일 변경 요약

- 수정: `src/math_variant/providers/structured.py`, `src/math_variant/agents/pipeline.py`,
  `src/math_variant/agents/*.py`(콜백 전달), `src/math_variant/api/app.py`,
  `src/math_variant/api/storage.py`, `web/src/app/page.tsx`, `web/src/lib/types.ts`,
  `web/src/lib/api.ts`
- 신규: `src/math_variant/api/events.py`, `src/math_variant/api/jobs.py`,
  `src/math_variant/api/problems.py`(또는 storage.py 확장), `src/math_variant/api/adapters.py`,
  `web/src/app/create/page.tsx`, `web/src/app/runs/[runId]/progress/page.tsx`,
  `web/src/app/problems/page.tsx`, web 컴포넌트 5개
- 테스트: `tests/unit/api/*`, `tests/unit/agents/*`(이벤트), `web/src/**/__tests__/*`

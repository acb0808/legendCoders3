# 웹 레퍼런스 레이어 노출 설계 — 진행상황·결과 페이지

## 목표

M1~M6으로 구현된 레퍼런스 주입 계층(기출 패턴·조건 표현 관례·교육과정 범위·해설
스타일 가이드·지식체계 스킬 매핑)을 웹 화면에서 확인하고 활용할 수 있게 한다.

1. 웹 생성 파이프라인을 **LangChain 엔진**으로 전환한다 (M6 스타일 정렬 포함).
   단, `MATH_VARIANT_PIPELINE_ENGINE=default` 환경변수로 기존 httpx 엔진 복귀 가능.
2. **진행상황 페이지**: 참조 검색·스킬 매핑·스타일 정렬을 새 단계로 표시한다.
3. **결과(검토) 페이지**: 단계별 스킬 매핑, 스타일 정렬 배지, 실행 단위 참조 요약
   패널을 표시한다.

## 사용자 결정 (2026-08-14)

- 엔진: 웹 기본 LangChain, 환경변수로 기존 엔진 복귀 가능.
- 진행상황: 새 단계 3개 추가 (참조 검색 / 스킬 매핑 / 스타일 정렬).
- 결과 페이지: ① 단계별 스킬 매핑 표시 ② 스타일 정렬 배지 ③ 참조 요약 패널 — 모두.

## 섹션 1: 백엔드 — 엔진 전환

- `src/math_variant/api/app.py` `PipelineRunner._execute`:
  - `MATH_VARIANT_PIPELINE_ENGINE` env가 `"default"`이면 기존 엔진, 그 외(미설정 포함)는
    `"langchain"`을 `build_pipeline(engine=...)`에 전달.
  - `enable_style_align`은 `MATH_VARIANT_STYLE_ALIGN` env 기본 `"1"`(켬)로 계산해 전달.
- `src/math_variant/pipeline_factory.py` `build_pipeline`:
  - `enable_style_align: bool | None = None` 파라미터 추가, LangChain 분기에서
    `build_langchain_pipeline`으로 전달만 한다. httpx 분기는 무시.
  - 팩토리·CLI 기본 동작 불변 (`MATH_VARIANT_STYLE_ALIGN` 기본 `"0"` 유지).

## 섹션 2: 백엔드 — 새 단계 이벤트 + 결과 데이터

### EventStage 확장 (`src/math_variant/events.py`)

```python
REFERENCE = "reference"          # 참조 검색
SKILL_MAPPING = "skill_mapping"  # 스킬 매핑
STYLE_ALIGN = "style_align"      # 스타일 정렬
```

`PipelineEvent.stage`는 `EventStage` 열거형이므로 `EventStage`에만 추가하면 양쪽
파이프라인이 재사용할 수 있다.

### 이벤트 발행

- 참조 검색 (`REFERENCE`): 기존에 `PLANNER` 단계로 발행하던 "참조 자산 검색 /
  참조 자산 주입 완료"를 이관한다.
  - httpx: `agents/pipeline.py` `run()` — `self.reference_runnable.invoke(...)` 전후.
  - LangChain: `langchain_generator/pipeline.py` `_enrich_references_node`.
  - `data`: `{"exam_patterns": N, "condition_phrasings": N, "style_unit": str | None}`.
- 스킬 매핑 (`SKILL_MAPPING`): `assign_skill_ids` 호출 전후 (후보별, `candidate_id` 포함).
  - httpx: `agents/pipeline.py` `_grow_candidate` (generator.generate 직후).
  - LangChain: `langchain_generator/pipeline.py` skill 매핑 호출부.
  - `data`: `{"matched": N, "total": N}`.
- 스타일 정렬 (`STYLE_ALIGN`): LangChain `_style_align_node`에서만 발행.
  - `data`: `{"applied": bool, "vocab": [...]}`.

### 결과 데이터 확장 (additive, 기존 스키마 비파괴)

- `PipelineReport` (`agents/pipeline.py`): `reference_summary: dict[str, Any] | None = None`
  추가. 형태:

  ```json
  {
    "exam_patterns": [{"topic_id", "unit", "pattern", "source_count"}],
    "condition_phrasings": {"count": N, "topics": ["..."]},
    "style_guide": {"unit": "...", "justification_vocab": ["..."]} | null
  }
  ```

  - httpx `run()`: `ref_res`에서 요약 생성.
  - LangChain: report 생성부에서 state의 `exam_patterns`/`condition_refs`/`style_guide`로 요약.
- `CandidateVerdict` (`agents/pipeline.py`): `style_aligned: bool = False` 추가.
  - LangChain `PipelineState`에 `style_aligned: bool` 추가, `_style_align_node`가 True 설정,
    `_verdict`가 `CandidateVerdict(style_aligned=...)`로 전달.
  - httpx는 항상 False (M6는 LangGraph 전용).
- `api/adapters.py` `_candidate_to_dict`: `"style_aligned"` 추가.
  `report_to_run_store`: `"reference_summary"` 추가 (None이면 생략하지 말고 `None` 유지).
- `api/storage.py` `public_run`: `reference_summary` 키를 반환 dict에 포함.

## 섹션 3: 진행상황 페이지

- `web/src/components/ProgressView.tsx`:
  - `STAGE_ORDER`: `planner` 뒤에 `reference`, `critic` 뒤에 `skill_mapping`·`style_align`.
  - `STAGE_LABELS`: `reference: "참조 검색"`, `skill_mapping: "스킬 매핑"`,
    `style_align: "스타일 정렬"`.
  - 기존 체크리스트 렌더링 로직 재사용 (변경 없음).

## 섹션 4: 결과(검토) 페이지

### 타입 (`web/src/lib/types.ts`)

```ts
export interface TransformationEvidence {
  dimension: string;
  step_id?: string;
  skill_id?: string | null;
  concept_name?: string;
  reason?: string;
  description?: string;
}

export interface Candidate {
  ...
  style_aligned?: boolean;
}

export interface GenerationRun {
  ...
  reference_summary?: ReferenceSummary | null;
}

export interface ReferenceSummary {
  exam_patterns: { topic_id: string; unit: string; pattern: string; source_count: number }[];
  condition_phrasings: { count: number; topics: string[] };
  style_guide: { unit: string; justification_vocab: string[] } | null;
}
```

`transformation_evidence: { dimension: string }[]` → `TransformationEvidence[]`.

### CandidateCard (`web/src/components/CandidateCard.tsx`)

- 변형 설명 목록: `dimension === "skill_mapping"` 항목은
  `단계 {step_id} → skill_id {skill_id} · {concept_name}` (또는 `reason`)으로 렌더.
  나머지는 기존 `{dimension}` 그대로.
- 해설 단계: `transformation_evidence`의 skill_mapping 항목을 `step_id`로 매칭해
  스킬 배지(skill_id·개념명)를 단계 옆에 표시. `skill_id`가 `null`(no_match)이면 배지 생략.
- 카드 헤더: `candidate.style_aligned === true`일 때 "스타일 정렬됨" 배지.

### ReviewClient (`web/src/app/runs/[runId]/review/ReviewClient.tsx`)

- run의 `reference_summary`가 있으면 후보 목록 위에 "참조 요약" 패널:
  - 기출 패턴: `unit · pattern` 목록 (source_count 포함).
  - 조건 관례: `count`건 + 토픽 목록.
  - 스타일 가이드: 단원 + 결론 어휘(`justification_vocab`).
- 없으면 패널 생략 (구버전 run 데이터 호환).

## 섹션 5: 테스트·품질 게이트

### 백엔드 (pytest)

- `tests/unit/agents/test_events.py`(또는 기존 이벤트 테스트): `EventStage`에 3개 값 존재.
- `tests/unit/api/test_adapters.py`: `reference_summary`·`style_aligned` 필드 반영 확인.
- `tests/unit/agents/test_pipeline.py`: httpx 파이프라인이 REFERENCE·SKILL_MAPPING
  이벤트를 발행하는지 (fake 에이전트).
- `tests/unit/langchain_generator/test_style_align.py`: `STYLE_ALIGN` 이벤트 발행 +
  `style_aligned` 상태 반영.

### 프론트 (vitest)

- `ProgressView.test.tsx`: 신규 3단계가 렌더되는지.
- `CandidateCard.test.tsx`: skill_mapping 렌더·스타일 정렬 배지.
- `ReviewClient`(있으면): 참조 요약 패널 렌더.

### 게이트

- 백엔드: `.venv\Scripts\python -m ruff check src tests scratch\build_*.py`,
  `.venv\Scripts\python -m mypy`, `.venv\Scripts\python -m pytest tests\unit -q`.
- 프론트: `web` 디렉터리에서 vitest·eslint (기존 스크립트 사용).
- `scratch\verify_parity.py` — 프롬프트 불변이므로 통과 유지 확인.

## 영향 파일

- 백엔드: `src/math_variant/events.py`, `agents/pipeline.py`,
  `langchain_generator/pipeline.py`, `pipeline_factory.py`, `api/app.py`,
  `api/adapters.py`, `api/storage.py`.
- 프론트: `web/src/components/ProgressView.tsx`, `CandidateCard.tsx`,
  `web/src/app/runs/[runId]/review/ReviewClient.tsx`, `web/src/lib/types.ts`.
- 테스트: `tests/unit/api/test_adapters.py`, `tests/unit/agents/test_pipeline.py`,
  `tests/unit/langchain_generator/test_style_align.py`,
  `web/src/components/__tests__/*`.

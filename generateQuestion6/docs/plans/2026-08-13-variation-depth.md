# 변형 깊이 강화 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 원본과 다른 수학 아이디어·구성으로 변형되도록 파이프라인을 개조한다 — Planner가 원본 구성을 "금지 구조"로 추출하고, Ideator/Generator가 이를 회피하며, 결정적 유사성 필터와 Critic이 원문 대비 참신성을 감시한다.

**Architecture:** 기존 다중 에이전트 파이프라인(planner→ideator→selector→generator→code_review→sandbox→blind→critic→judge) 구조는 유지한다. Planner 출력에 `forbidden_structure`(원본 구성 골격)를 추가하고 이를 ideator/generator/critic에 전달한다. 신규 비LLM 유사성 필터(`services/similarity.py`)가 후보의 표현 복제를 결정적으로 차단한다. 원문 텍스트는 발상·선별·생성 단계에는 여전히 노출하지 않고, Critic의 참신성 비교와 유사성 필터에만 사용한다.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, pytest, Next.js(변경 없음 — 백엔드만).

---

## 작업 환경 규칙

- 프로젝트 루트: `generateQuestion6/` (git 루트는 상위 `Coding`, 브랜치 `codex/generatequestion2`, 스테이징 경로는 `generateQuestion6/...`)
- venv 파이썬: `.venv\Scripts\python.exe`
- 게이트: `pytest`(전체), `ruff check src tests infra`, `mypy`
- 프롬프트 파일: `src/math_variant/prompts/*.md` — `.md`는 프롬프트 본문일 뿐 코드가 아니므로 pytest 대상 아님
- 각 Task 완료 후 커밋. 커밋 경로는 반드시 `generateQuestion6/...` (상위 루트에 시험지 등 다른 프로젝트가 있으므로 `git add` 시 정확한 경로만 스테이징)

---

### Task 1: PlannerOutput 에 forbidden_structure 필드 추가

**Files:**
- Modify: `src/math_variant/agents/schemas.py:32-44` (PlannerOutput)
- Modify: `src/math_variant/prompts/planner.md`
- Test: `tests/unit/agents/test_schemas.py:44`

**Step 1: 스키마에 필드 추가**

`src/math_variant/agents/schemas.py`의 `PlannerOutput`에 다음 필드를 추가한다:

```python
    preservation_goals: list[str] = Field(min_length=1)
    forbidden_structure: list[str] = Field(min_length=1)  # 원본 문제의 구성 골격 (재사용 금지)
    strategy: ProductionStrategy
```

**Step 2: 테스트 데이터 수정**

`tests/unit/agents/test_schemas.py`의 `_planner()` 헬퍼와 `tests/unit/api/test_adapters.py`의 `_planner()`에 `"forbidden_structure": ["직선 위 점에서 축에 수선", "삼각형 넓이 조건"]` 을 추가한다.

**Step 3: 프롬프트 갱신**

`src/math_variant/prompts/planner.md` 수정:
- "## 원칙"에 추가: "보존 목표는 단원(개념 어휘·exam_scope)·난이도로 한정한다. 원본 문제의 구성 자체는 보존하지 않는다. 다음 단계가 원본과 같은 구성을 재사용하지 않도록, 원본 문제의 구성 골격(객체 배치·관계·목표 형태)을 `forbidden_structure` 로 구조적으로 요약한다."
- 스키마 예시 JSON에 `"forbidden_structure": [...]` 추가.
- 스키마 설명에 "forbidden_structure: 배열(list of strings), 최소 1개" 추가.

**Step 4: 테스트 실행**

Run: `.venv\Scripts\python -m pytest tests/unit/agents/test_schemas.py tests/unit/api/test_adapters.py -q`
Expected: PASS (스키마·고정 필드 검증 포함)

**Step 5: 전체 게이트 + 커밋**

```bash
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check src tests infra
.venv\Scripts\python -m mypy
git -C .. add generateQuestion6/src/math_variant/agents/schemas.py generateQuestion6/src/math_variant/prompts/planner.md generateQuestion6/tests/unit/agents/test_schemas.py generateQuestion6/tests/unit/api/test_adapters.py
git -C .. commit -m "feat: add forbidden_structure to planner output"
```

---

### Task 2: Ideator 가 forbidden_structure 를 받아 다른 구성으로 전환

**Files:**
- Modify: `src/math_variant/agents/ideator.py:14-36` (build_ideation_brief)
- Modify: `src/math_variant/agents/pipeline.py:186-193` (build_ideation_brief 호출부)
- Modify: `src/math_variant/prompts/ideator.md`
- Test: `tests/unit/agents/test_planner_ideator_selector.py:91`

**Step 1: build_ideation_brief 에 파라미터 추가**

`src/math_variant/agents/ideator.py`의 `build_ideation_brief`:

```python
def build_ideation_brief(
    *,
    core_concepts: list[str],
    objective: str,
    answer_type: str,
    domain: str,
    preservation_goals: list[str],
    forbidden_structure: list[str] | None = None,
    strategy: ProductionStrategy,
) -> str:
```

본문에 다음 줄을 추가한다 (보존 목표 뒤):

```python
        f"- 보존 목표: {preservation_goals}\n"
        f"- 금지 구조(원본 구성 골격, 재사용 금지): {forbidden_structure or []}\n"
```

**Step 2: pipeline 호출부에 forbidden_structure 전달**

`src/math_variant/agents/pipeline.py:186-193`의 `build_ideation_brief(...)` 호출에 `forbidden_structure=planner_out.forbidden_structure,` 를 추가한다.

**Step 3: 프롬프트 갱신**

`src/math_variant/prompts/ideator.md`:
- "## 원칙"에 추가: "같은 단원 범위에서 원본과 **다른 수학 아이디어·문제 구성**으로 전환한다. `금지 구조` 에 나열된 구성(객체 배치·관계·목표 형태)을 재사용하지 않는다."
- `construction_blueprint` 지침 강화: "숫자만 바꾸는 blueprint 금지. 어떤 객체·관계·목표로 새 문제를 만들지 구체적으로 스케치한다."

**Step 4: 기존 테스트 확인/수정**

`tests/unit/agents/test_planner_ideator_selector.py:91` — `build_ideation_brief` 호출에 인자 추가(선택: `forbidden_structure=["..."]`). 기본값이 있어 기존 호출도 동작한다. 전달 확인 단위 테스트 추가:

```python
def test_ideation_brief_includes_forbidden_structure() -> None:
    brief = build_ideation_brief(
        core_concepts=["포물선"], objective="o", answer_type="expression",
        domain="d", preservation_goals=["p"],
        forbidden_structure=["직선 위 점에서 수선", "삼각형 넓이"],
        strategy=ProductionStrategy.model_validate(_PLANNER_DATA["strategy"]),
    )
    assert "직선 위 점에서 수선" in brief
    assert "재사용 금지" in brief
```

**Step 5: 테스트 + 커밋**

```bash
.venv\Scripts\python -m pytest tests/unit/agents/test_planner_ideator_selector.py -q
git -C .. add generateQuestion6/src/math_variant/agents/ideator.py generateQuestion6/src/math_variant/agents/pipeline.py generateQuestion6/src/math_variant/prompts/ideator.md generateQuestion6/tests/unit/agents/test_planner_ideator_selector.py
git -C .. commit -m "feat: pass forbidden structure to ideator for fresh compositions"
```

---

### Task 3: Generator 가 금지 구조 재사용을 피하도록 프롬프트 확장

**Files:**
- Modify: `src/math_variant/agents/generator.py:49-60` (_build_prompt)
- Modify: `src/math_variant/agents/pipeline.py:308-321` (blueprint_dict 구성부)
- Modify: `src/math_variant/prompts/candidate_generator.md`
- Test: `tests/unit/agents/test_generator_and_verifiers.py`

**Step 1: _build_prompt 에 forbidden_structure 전달**

`src/math_variant/agents/generator.py`의 `_build_prompt(self, blueprint, brief, feedback)` 시그니처에 `forbidden_structure: list[str] | None = None` 추가, 본문:

```python
        if forbidden_structure:
            prompt += f"[금지 구조 (원본 구성 골격, 재사용 금지)]\n- {forbidden_structure}\n"
```

`generate()`에서 `self._build_prompt(blueprint, brief, feedback, forbidden_structure)` 호출. `generate()` 시그니처에 `forbidden_structure: list[str] | None = None` 파라미터 추가.

**Step 2: pipeline 에서 전달**

`src/math_variant/agents/pipeline.py` `_grow_candidate`의 `self.generator.generate(...)` 호출에 `forbidden_structure=self._forbidden_structure` 전달. `_forbidden_structure`는 `_grow_candidate`/`_generate_and_verify`를 통해 내려받는다 (Task 6에서 배선, 이 Task에서는 기본값으로 빈 목록 유지).

**Step 3: 프롬프트 갱신**

`src/math_variant/prompts/candidate_generator.md`의 "## 원칙"에 추가: "`금지 구조` 의 구성 골격을 그대로 다시 쓰지 않는다. 같은 단원에서 다른 수학 아이디어로 문제를 구성한다. 원문 문구를 모르므로 인용·복사는 원천 불가다."

**Step 4: 테스트 + 커밋**

```bash
.venv\Scripts\python -m pytest tests/unit/agents/test_generator_and_verifiers.py -q
git -C .. add generateQuestion6/src/math_variant/agents/generator.py generateQuestion6/src/math_variant/agents/pipeline.py generateQuestion6/src/math_variant/prompts/candidate_generator.md
git -C .. commit -m "feat: keep generator from reusing the original problem structure"
```

---

### Task 4: 결정적 표현 유사성 필터 (services/similarity.py)

**Files:**
- Create: `src/math_variant/services/similarity.py`
- Test: `tests/unit/services/test_similarity.py`

**Step 1: 실패 테스트 작성**

```python
# tests/unit/services/test_similarity.py
from math_variant.services.similarity import (
    SimilarityReport,
    longest_common_substring,
    ngram_similarity,
    normalize_text,
    similarity_report,
)


def test_normalize_strips_punctuation_and_space() -> None:
    assert normalize_text("직선 y=-x+3 위의 점 P, O(0,0)") == "직선yx3위의점PO00"


def test_lcs_long_reuse_detected() -> None:
    a = normalize_text("직선 위의 점 P에서 x축에 내린 수선의 발을 H라 한다")
    b = normalize_text("직선 위의 점 P에서 x축에 내린 수선의 발을 H라 하고 넓이를 구하라")
    assert longest_common_substring(a, b) > 20


def test_ngram_similarity_high_for_copied_sentence() -> None:
    a = normalize_text("삼각형 OPH의 넓이가 9가 되도록 하는 점 P의 좌표를 구하시오")
    b = normalize_text("삼각형 OPH의 넓이가 9가 되도록 하는 점 P의 좌표를 구하시오")
    assert ngram_similarity(a, b) > 0.8


def test_ngram_low_for_different_problem() -> None:
    a = normalize_text("직선 위 점에서 축에 수선을 내려 삼각형 넓이를 구한다")
    b = normalize_text("포물선과 직선의 교점 사이의 거리를 구한다")
    assert ngram_similarity(a, b) < 0.3


def test_report_flags_copy_with_snippet() -> None:
    source = "직선 위의 점 P에서 x축에 내린 수선의 발을 H라 하면 삼각형 OPH의 넓이가 9이다."
    candidate = "직선 위의 점 P에서 x축에 내린 수선의 발을 H라 하면 삼각형 OPH의 넓이가 9가 되는 P를 구하시오."
    report = similarity_report(source, candidate)
    assert report.too_similar is True
    assert report.lcs_len > 20
    assert "삼각형" in report.match_snippet or "OPH" in report.match_snippet


def test_report_pass_for_different_problem() -> None:
    source = "직선 위의 점에서 축에 내린 수선과 삼각형 넓이를 이용한다."
    candidate = "포물선 y=ax^2와 직선 y=x+3의 두 교점 사이의 거리를 구하시오."
    report = similarity_report(source, candidate)
    assert report.too_similar is False
```

**Step 2: 구현**

```python
# src/math_variant/services/similarity.py
"""원문 vs 후보의 결정적(비LLM) 표현 유사성 검사.

표현 복제(원문 문장을 그대로 쓰는 문제)를 차단하기 위한 보조 필터다.
아이디어 수준의 참신성은 Critic 이 담당하고, 여기서는 문자열 유사성을 결정적으로
판정해 "어느 구간이 일치하는지" 까지 보고한다 (피드백 루프 입력).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_STRIP = re.compile(r"[\s\u3000，。！？·、·\.\.,:;:()\[\]{}<>\"'‘’“”=+\-*/^_\\|~`!@#$%&]")

_LCS_THRESHOLD = 20     # 최장 공통 부분문자열 최대 길이 기준
_NGRAM_THRESHOLD = 0.55  # 문자 3-gram 유사도 기준


def normalize_text(text: str) -> str:
    """공백·구두점·수식 기호를 제거해 비교 가능한 형태로 만든다."""
    return _STRIP.sub("", text)


def longest_common_substring(a: str, b: str) -> tuple[int, int, int]:
    """최장 공통 부분문자열 (길이, a 시작 인덱스, b 시작 인덱스)."""
    if not a or not b:
        return 0, 0, 0
    prev = [0] * (len(b) + 1)
    best = 0
    best_a = 0
    best_b = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
                    best_a = i - best
                    best_b = j - best
        prev = cur
    return best, best_a, best_b


def ngram_similarity(a: str, b: str, n: int = 3) -> float:
    """문자 n-gram 의 Jaccard 유사도."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    grams_a = {a[i : i + n] for i in range(len(a) - n + 1)}
    grams_b = {b[i : i + n] for i in range(len(b) - n + 1)}
    if not grams_a or not grams_b:
        return 0.0
    return len(grams_a & grams_b) / len(grams_a | grams_b)


@dataclass(frozen=True)
class SimilarityReport:
    too_similar: bool
    lcs_len: int
    ngram_score: float
    match_snippet: str = ""


def similarity_report(source_text: str, candidate_text: str) -> SimilarityReport:
    """원문과 후보의 표현 유사성을 판정한다. 일치 구간 스니펫을 포함한다."""
    src = normalize_text(source_text)
    cand = normalize_text(candidate_text)
    if not src or not cand:
        return SimilarityReport(False, 0, 0.0)
    lcs_len, a_start, _b_start = longest_common_substring(src, cand)
    ngram = ngram_similarity(src, cand)
    too_similar = lcs_len > _LCS_THRESHOLD or ngram > _NGRAM_THRESHOLD
    snippet = src[a_start : a_start + lcs_len] if too_similar else ""
    return SimilarityReport(too_similar, lcs_len, ngram, snippet)
```

**Step 3: 테스트 통과 확인 + 커밋**

```bash
.venv\Scripts\python -m pytest tests/unit/services/test_similarity.py -q
git -C .. add generateQuestion6/src/math_variant/services/similarity.py generateQuestion6/tests/unit/services/test_similarity.py
git -C .. commit -m "feat: add deterministic lexical similarity filter with match report"
```

---

### Task 5: Critic 이 원문 대비 참신성을 평가

**Files:**
- Modify: `src/math_variant/agents/critic.py:18-26`
- Modify: `src/math_variant/prompts/critic.md`
- Test: `tests/unit/agents/test_generator_and_verifiers.py:116,141`

**Step 1: criticize 시그니처 확장 (기본값 부여 → 기존 호출 유지)**

```python
    def criticize(
        self,
        problem_text: str,
        spec_brief: str,
        strategy_brief: str,
        candidate_id: str = "critic",
        source_text: str = "",
        forbidden_structure: list[str] | None = None,
    ) -> CriticOutput:
        prompt = (
            f"{self.prompt_bundle}\n\n"
            f"[문제 후보]\n{problem_text}\n"
            f"[문제 구조]\n{spec_brief}\n"
            f"[변형 전략]\n{strategy_brief}"
        )
        if source_text:
            prompt += f"\n[원본 문항 (참신성 비교용 — 복사·출력 금지, 평가에만 사용)]\n{source_text}\n"
        if forbidden_structure:
            prompt += f"[원본 구성 골격 (동일 골격 재사용은 낮은 점수)]\n- {forbidden_structure}\n"
```

**Step 2: 프롬프트 갱신**

`src/math_variant/prompts/critic.md`:
- "## 입력"에 "[원본 문항(참신성 비교용)]", "[원본 구성 골격]" 추가.
- "## 원칙"에 추가:
  - "표현 복제 검사: 후보 문장이 원본 문장과 겹치면 novelty 를 크게 낮춘다."
  - "구성 아이디어 동일 검사: 후보의 객체 배치·관계·목표 형태가 원본 구성 골격과 동일한 골격이면 novelty 를 낮추고 REVISE/REJECT 를 권한다."
  - "원본 문항은 참신성 비교에만 사용한다. 후보·산출물에 원문을 포함하지 않는다."

**Step 3: 테스트 + 커밋**

```bash
.venv\Scripts\python -m pytest tests/unit/agents/test_generator_and_verifiers.py -q
git -C .. add generateQuestion6/src/math_variant/agents/critic.py generateQuestion6/src/math_variant/prompts/critic.md
git -C .. commit -m "feat: critic novelty now compares against the original problem"
```

---

### Task 6: pipeline 배선 — 원문·금지 구조 전달 + 유사성 필터 통합

**Files:**
- Modify: `src/math_variant/agents/pipeline.py`

**Step 1: _generate_and_verify / _grow_candidate 에 원문·금지 구조 전달**

- `_run` 의 `self._generate_and_verify(run_id, adopted, ideation_brief, strategy_brief)` 호출에
  `source_text=source_text, forbidden_structure=planner_out.forbidden_structure` 추가.
- `_generate_and_verify(...)` 시그니처에 `source_text: str`, `forbidden_structure: list[str] | None = None` 추가, `_grow_candidate(...)` 호출에 전달.
- `_grow_candidate(...)` 시그니처에 동일 인자 추가.
  - `self.generator.generate(...)` 호출에 `forbidden_structure=forbidden_structure` 전달 (Task 3).
  - `self.critic.criticize(..., source_text=source_text, forbidden_structure=forbidden_structure)` 전달 (Task 5).

**Step 2: 결정적 유사성 필터 배선 (구체 피드백 → REVISE 재시도)**

`_grow_candidate` 에서 generator 직후, code_review 이전에:

```python
        from math_variant.services.similarity import similarity_report

        report = similarity_report(source_text, candidate.problem_text)
        if report.too_similar:
            feedback = (
                f"[참신성 피드백] 원문과 '{report.match_snippet}' 구간이 일치합니다. "
                "같은 단원에서 이 구성과 다른 수학 아이디어로 문제를 다시 구성하세요."
            )
            self._emit(
                EventStage.GENERATION, "failed",
                f"원문과 표현이 유사 (일치 {report.lcs_len}자) — 재생성", candidate_id,
            )
            # REVISE 재귀(max_refine 한도)로 재생성한다
            return self._grow_candidate(
                run_id, candidate_id, blueprint, ideation_brief, strategy_brief,
                source_text=source_text, forbidden_structure=forbidden_structure,
                feedback=feedback, attempts=attempts + 1,
            )
```

- `_grow_candidate` 가 `attempts > self.max_refine` 인데도 유사하면 REVISE 로직처럼 재귀를 계속하지 않고
  폐기(UNRESOLVED)한다. 즉 유사성 위반 재귀도 `attempts` 한도를 공유한다:
  재귀 진입 전 `if attempts >= self.max_refine: status="UNRESOLVED"` 처리로 폐기.
- Critic novelty 낮음(REVISE)은 기존 경로로 `review.feedback or "; ".join(critic.comments)` 를
  feedback 으로 재생성한다. Task 5 의 "구체적 수정 지시" 지침 덕에 critic.comments 가
  참신성 개선 지시를 담는다.

**Step 3: 참신성 피드백 루프 통합 테스트 추가**

`tests/unit/agents/test_pipeline_revision.py` (신규):

```python
def test_candidate_copying_source_expression_is_revised_with_snippet() -> None:
    # generator stub 이 원문과 같은 문장을 반환하도록 설정
    # → similarity_report.too_similar == True
    # → verdict.status 가 REVISE(시도 한도 내)이고,
    #   생성자에 전달된 feedback 에 "일치" 문구와 스니펫이 포함됐는지 확인
```

**Step 4: 전체 게이트 + 커밋**

```bash
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check src tests infra
.venv\Scripts\python -m mypy
git -C .. add generateQuestion6/src/math_variant/agents/pipeline.py generateQuestion6/tests/unit/agents/test_pipeline_revision.py
git -C .. commit -m "feat: enforce deeper variation in the pipeline (novelty feedback loop)"
```

---

### Task 7: 회귀 확인 및 라이브 검증

**Step 1: 전체 게이트**

```bash
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check src tests infra
.venv\Scripts\python -m mypy
```

Expected: 기존 테스트 전부 통과 (기본값 부여로 기존 호출 유지됨).

**Step 2: 서버 재시작 + 라이브 실행**

- 8000 포트 프로세스 종료 후 `.venv\Scripts\python -m uvicorn math_variant.api.app:app --host 127.0.0.1 --port 8000` 재기동
  (WMI/Start-Process -WindowStyle Hidden 사용, workdir=프로젝트 루트).
- `/api/generations` 로 생성 요청 → 완료까지 대기.
- 완료된 run 의 `/api/runs/{run_id}` 에서 후보의 `problem_text` 와 원본 `source.text` 비교:
  - 표현 복제 없음 (결정적 필터)
  - forbidden_structure 의 구성 골격(직선 위 점→수선→삼각형 넓이→좌표 결정)이 아닌 다른 구성인지 수동 확인

**Step 3: 최종 커밋 확인**

`git -C .. log --oneline -8` 로 Task 1~6 커밋이 쌓였는지 확인.

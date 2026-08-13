# 변형 깊이 강화 — "같은 범위, 다른 아이디어" 아키텍처

> 상태: 사용자 승인 완료 (2026-08-13).
> 다음 단계: writing-plans 로 구현 계획 수립.

## 배경 (문제 진단)

생성된 후보 문제들이 원본과 유사하다는 사용자 피드백이 있었다.

- 원본 표현을 그대로 쓰거나
- 아이디어 원리(문제 구성 템플릿)가 원본과 똑같은 경우가 대부분

기존 run 산출물 검토에서 확인된 근본 원인:

1. **Planner 가 원본의 문제 구성을 "보존 목표"로 고정** — 예를 들어 "직선 위 점 → 축에 수선 → 삼각형 넓이 → 직선 결정" 같은 구성이
   `preservation_goals` 로 내려가 Ideator 는 그 구조 안에서만 수치·이름·표기를 바꾼다.
2. **Critic 이 원문을 못 봐서** "원본과 같은 아이디어/표현" 을 걸러낼 수 없다.
   참신성(novelty) 점수는 스펙·전략 대비로만 평가되어 원본 대비 유사성은 판정 불가.
3. **changed_dimensions 는 라벨뿐** — 실질적인 구성 교체를 강제하지 않는다.

## 사용자 결정

1. **변형 깊이**: "같은 범위 내 다른 개념으로 전환" — 단원 범위(예: 도형의 방정식) 안에서
   원본이 쓰는 수학 아이디어 자체를 바꾼다.
2. **보존 기준**: "단원·난이도만 보존" — 학습 목표·문제 구성은 보존하지 않는다.
3. **접근 조합**: 안 A(금지 구조 + Critic 참신성) + 안 C(결정적 표현 유사성 필터).

## 접근 방식

기존 파이프라인 구조(planner → ideator → selector → generator → code_review →
sandbox → blind → critic → judge)는 유지하되, 각 단계가 "원본 구성 금지"를
명시적으로 전달·감시하도록 확장한다. 원문 텍스트는 여전히 발상·선별·생성 단계에는
노출되지 않는다. (원문을 보는 것은 Critic 의 참신성 비교와 결정적 유사성 필터뿐)

---

## 섹션 1: Planner — 원본 구성을 "금지 구조"로 전환

### 변경
- 출력 스키마에 `forbidden_structure: list[str]` 를 추가한다 (필수, 최소 1개).
- `forbidden_structure` 는 원본 문제의 **구성 아이디어 템플릿**을 구조적으로 요약한 목록이다.
  예: `["좌표평면 위 직선 위의 점", "점에서 축에 내린 수선", "삼각형 넓이 조건", "직선·점 좌표 결정"]`
- 프롬프트 지침을 바꾼다:
  - 보존 목표는 **단원(개념 어휘·exam_scope)·난이도 목표**로 한정한다.
  - "원본 문제의 구성 자체는 보존하지 않는다. 다음 단계가 원본과 같은 구성을 재사용하지
    않도록 원본 구성의 골격을 forbidden_structure 로 남긴다."
- `variation_direction` 에 같은 단원 내 다른 수학 아이디어로의 전환을 구체적으로 제시하도록 강화한다.

### 스키마
```json
{
  "core_concepts": ["포물선"],
  "auxiliary_concepts": [],
  "objective": "상수의 값을 구하시오",
  "answer_type": "expression",
  "domain": "도형의 방정식",
  "preservation_goals": ["이차함수·직선의 관계 이해"],
  "forbidden_structure": ["직선 위 점에서 축에 수선", "삼각형 넓이 조건", "점 좌표 결정"],
  "strategy": { "difficulty_target": "중상", "preservation_goals": [], "variation_direction": [], "quality_criteria": [], "constraints": [] },
  "unresolved_assumptions": []
}
```

### 영향 파일
- `src/math_variant/agents/schemas.py` (PlannerOutput)
- `src/math_variant/agents/planner.py`
- `src/math_variant/prompts/planner.md`

---

## 섹션 2: Ideator — 금지 구조를 피한 전환 강제

### 변경
- 발상 입력(brief)에 `forbidden_structure` 를 포함해 전달한다.
- 프롬프트 지침:
  - "같은 단원 범위에서 원본과 다른 수학 아이디어·문제 구성으로 전환한다."
  - "forbidden_structure 와 같은 구성(객체 배치·관계·목표 형태)을 재사용하지 않는다."
  - `construction_blueprint` 를 구체적인 **새 구성 스케치**(어떤 객체·관계·목표로 만들지)로
    작성하도록 강제한다. "숫자만 바꾼다" 식의 blueprint 는 금지.
- `changed_dimensions` 검증: 구성 교체가 실제로 포함되도록 예시와 검사 지침을 강화한다.

### 영향 파일
- `src/math_variant/agents/ideator.py` (`build_ideation_brief`)
- `src/math_variant/prompts/ideator.md`

---

## 섹션 3: Generator — 금지 구조 재사용 금지 명시

### 변경
- 생성 프롬프트에 `forbidden_structure` 를 전달한다 (원문 텍스트는 여전히 미노출).
- 프롬프트 지침:
  - "forbidden_structure 의 구성 골격을 그대로 다시 쓰지 않는다. 같은 단원에서 다른
    수학 아이디어로 문제를 구성한다."
  - "원문 문구를 모르므로 인용·복사가 불가능하다. 오직 새 구성으로만 문제를 쓴다."

### 영향 파일
- `src/math_variant/agents/generator.py` (`_build_prompt`)
- `src/math_variant/prompts/candidate_generator.md`

---

## 섹션 4: 결정적 표현 유사성 필터 (비LLM)

신규 `src/math_variant/services/similarity.py`.

### 동작
- 원문 텍스트(정규화)와 후보 `problem_text`(정규화)를 비교한다.
- 정규화: 공백·구두점·기호 제거, 소문자 통일, 수치·변수 토큰은 형태 유지.
- 두 검사:
  1. **최장 공통 부분문자열(LCS)**: 길이가 임계값(기본 20자) 초과 시 위반.
  2. **문자 3-gram 유사도**: 유사도 > 임계값(기본 0.55) 시 위반.
- 위반 시 후보는 critic 판정과 무관하게 즉시 REJECT 처리된다.

### 배선 (pipeline)
- `_grow_candidate` 에서 generator 이후, code_review 이전에 실행.
- 위반이면 REVISE 피드백("원문 표현·구성이 재사용됐다")으로 재생성 재시도(max_refine 내).

### 테스트
- 정규화·LCS·3-gram 단위 테스트, 위반/통과 케이스.

---

## 섹션 5: Critic — 원문 대비 참신성 점수화

### 변경
- `criticize()` 에 원문 텍스트(`source_text`)와 `forbidden_structure` 를 비교용으로 전달한다.
  (Critic 의 출력은 점수·코멘트뿐이라 원문 누출 위험이 없다)
- 프롬프트 지침 추가:
  - **표현 복제 검사**: 후보 문장이 원문 문장과 겹치면 novelty 를 크게 낮춘다.
  - **구성 아이디어 동일 검사**: 후보의 객체 배치·관계·목표 형태가 forbidden_structure 와
    동일한 골격이면 novelty 를 낮추고 REVISE/REJECT 를 권한다.
- `criteria_scores.novelty` 가 낮으면 전체 score 가 낮아지도록 가중치 지침을 명시한다.

### 영향 파일
- `src/math_variant/agents/critic.py`
- `src/math_variant/prompts/critic.md`
- `src/math_variant/agents/pipeline.py` (원문 전달 배선)

---

## 데이터 흐름

```
원문(source_text)
  └─ planner ─► brief { core_concepts, forbidden_structure, strategy(단원·난이도), ... }
        └─► ideator ×N  (forbidden_structure 회피, 새 구성 blueprint)
              └─► selector
                    └─► generator (forbidden_structure 재사용 금지)
                          └─► [결정적 유사성 필터] ─위반─► REVISE (재생성)
                          └─► code_review → sandbox
                          └─► blind
                          └─► critic (원문 + forbidden_structure 대비 참신성) ─낮으면─► REVISE | REJECT
```

## 오류 처리

- planner 가 forbidden_structure 를 만들지 못하면 스키마 검증 실패로 기존처럼 재시도한다.
- 유사성 필터가 모든 후보를 위반 처리하면 기존 `AGENT_UNRESOLVED` 경로로 실패한다.
- Critic 이 원문을 받는 것은 참신성 비교 전용이며, 후보·산출물에 원문을 포함하지 않도록
  프롬프트에 명시한다.

## 테스트 계획

- 단위: PlannerOutput 스키마(forbidden_structure), similarity(정규화/LCS/3-gram),
  critic 프롬프트 인자, ideator brief 에 forbidden_structure 포함.
- 통합: `_grow_candidate` 에서 필터 위반 → REVISE 재시도, critic novelty 반영.
- live: 같은 원문으로 변형 후 원본 구성이 재사용되지 않는지 수동 확인.

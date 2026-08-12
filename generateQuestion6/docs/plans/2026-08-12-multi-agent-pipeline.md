# 다중 에이전트 병렬 파이프라인 + 반복 개선 루프 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 원문(2023 광명북고 Q19 포물선·평행이동·중점)을 LLM 다중 에이전트(기획→발상→선별→생성→검증→집계→개선)로 변형한 신규 문항을 생산하되, 원문 본문은 기획자에게만 노출하고 발상·생성·선별 에이전트는 원문 없이 스펙·청사진만 받아 창의적 변형을 유도하며, 생성기의 답은 "LLM이 쓴 sympy 검증 스크립트 → 코드리뷰 → 격리 샌드박스 실행"으로 독립 검증한다.

**Architecture:** 기존 `RolePolicy`(공급자·모델·temperature 설정 주도)와 `StructuredOutputEngine`(구조화 출력 + 복구 + 폴백)을 그대로 재사용한다. 새 역할(PLANNER/IDEATOR/SELECTOR/CODE_REVIEWER/JUDGE/VISION)을 설정에 등록하고, `src/math_variant/agents/`에 에이전트 서비스와 병렬 오케스트레이터를 추가한다. 텍스트 역할 전부는 `deepseek-v4-flash`, 도형 렌더링(VISION)만 `gpt-5.6-luna`(TikZ 코드 생성 → `runs/figures/*.tex`)로 둔다. 검증 스크립트 실행은 기존 Docker 샌드박스(`math-variant-sandbox:test`)를 provider로 주입한다.

**Tech Stack:** Python 3.12, pydantic v2(`extra="forbid"` 스키마), pydantic-settings, ThreadPoolExecutor, Docker 샌드박스, sympy(검증 스크립트), ruff/mypy-strict/pytest(품질 게이트).

**원문 접근 경계 (사용자 결정):**
- 원문 본문 제공: **PLANNER** 만.
- 미제공: IDEATOR, SELECTOR, GENERATOR (스펙·전략·청사진·피드백만).
- BLIND_SOLVER: 후보 문제 본문만.
- CRITIC/JUDGE: 후보 + 스펙·전략 (원문 없음).

**Temperature 설정 (사용자 결정):** IDEATOR=1.4(발산), SELECTOR=0.3, GENERATOR=0.7, PLANNER=0.2, CODE_REVIEWER=0.2, CRITIC=0.2, JUDGE=0.2, VISION=0.4.

---

## Task 1: 역할 정책과 기본 역할 설정 확장

**Files:**
- Modify: `src/math_variant/providers/contracts.py:11-17` (RolePolicy enum)
- Modify: `src/math_variant/providers/settings.py` (기본 역할 맵)
- Modify: `src/math_variant/errors.py:16-50` (ErrorCode 추가)
- Create: `tests/unit/providers/test_settings_roles.py`

**Step 1: 실패 테스트 작성**

`tests/unit/providers/test_settings_roles.py`:
```python
"""다중 에이전트 역할 정책 기본값·재정의 테스트."""

from __future__ import annotations

from math_variant.providers.contracts import RolePolicy
from math_variant.providers.settings import ProviderSettings


def test_default_roles_include_new_agents_with_high_ideator_temperature() -> None:
    roles = ProviderSettings(_env_file=None).role_policy().roles
    assert roles[RolePolicy.PLANNER].provider == "deepseek"
    assert roles[RolePolicy.IDEATOR].temperature >= 1.3
    assert roles[RolePolicy.SELECTOR].temperature < 1.0
    assert roles[RolePolicy.CODE_REVIEWER].temperature <= 0.3
    assert roles[RolePolicy.JUDGE].temperature <= 0.3
    assert roles[RolePolicy.GENERATOR].temperature == 0.7


def test_vision_role_uses_luna_provider() -> None:
    roles = ProviderSettings(_env_file=None).role_policy().roles
    vision = roles[RolePolicy.VISION]
    assert vision.provider == "openai"
    assert vision.model == "gpt-5.6-luna"


def test_text_roles_default_to_deepseek_flash_model() -> None:
    roles = ProviderSettings(_env_file=None).role_policy().roles
    for role in (RolePolicy.PLANNER, RolePolicy.IDEATOR, RolePolicy.SELECTOR,
                 RolePolicy.CODE_REVIEWER, RolePolicy.JUDGE):
        assert roles[role].model == "deepseek-chat"  # deepseek_model_flash 기본값


def test_role_policy_json_override_for_new_role() -> None:
    settings = ProviderSettings(
        _env_file=None,
        role_policy_json='{"ideator": {"provider": "openai", "model": "gpt-5.6-luna", "temperature": 1.6}}',
    )
    entry = settings.role_policy().roles[RolePolicy.IDEATOR]
    assert entry.provider == "openai"
    assert entry.model == "gpt-5.6-luna"
    assert entry.temperature == 1.6
```

> 참고: `ProviderSettings(_env_file=None)` 로 `.env` 없이 순수 기본값을 검증한다. `.env`의 `DEEPSEEK_MODEL_FLASH=deepseek-v4-flash` 때문에 기본 `deepseek-chat` 폴백 모델로 테스트한다(flash 모델은 설정 존재 시 사용).

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/providers/test_settings_roles.py -v`
Expected: FAIL — `RolePolicy`에 새 멤버가 없어 ImportError.

**Step 3: 구현**

`contracts.py` — RolePolicy enum에 추가:
```python
class RolePolicy(StrEnum):
    """모델명 대신 비즈니스 코드가 참조하는 역할 정책."""

    SOURCE_ANALYZER = "source_analyzer"
    GENERATOR = "generator"
    BLIND_SOLVER = "blind_solver"
    CRITIC = "critic"
    PLANNER = "planner"
    IDEATOR = "ideator"
    SELECTOR = "selector"
    CODE_REVIEWER = "code_reviewer"
    JUDGE = "judge"
    VISION = "vision"
```

`settings.py` — `_DEFAULT_ROLES`를 함수로 교체하고 텍스트 역할 전부를 flash 모델로 통일:
```python
def _default_roles(flash_model: str) -> dict[RolePolicy, RolePolicyEntry]:
    """텍스트 역할은 deepseek flash 모델, VISION(도형 렌더링)만 luna 로 고정한다."""
    return {
        RolePolicy.SOURCE_ANALYZER: RolePolicyEntry(
            provider="deepseek", model=flash_model, temperature=0.2
        ),
        RolePolicy.GENERATOR: RolePolicyEntry(
            provider="deepseek", model=flash_model, temperature=0.7
        ),
        RolePolicy.BLIND_SOLVER: RolePolicyEntry(
            provider="deepseek", model=flash_model, temperature=0.2
        ),
        RolePolicy.CRITIC: RolePolicyEntry(
            provider="deepseek", model=flash_model, temperature=0.2
        ),
        RolePolicy.PLANNER: RolePolicyEntry(
            provider="deepseek", model=flash_model, temperature=0.2
        ),
        RolePolicy.IDEATOR: RolePolicyEntry(
            provider="deepseek", model=flash_model, temperature=1.4
        ),
        RolePolicy.SELECTOR: RolePolicyEntry(
            provider="deepseek", model=flash_model, temperature=0.3
        ),
        RolePolicy.CODE_REVIEWER: RolePolicyEntry(
            provider="deepseek", model=flash_model, temperature=0.2
        ),
        RolePolicy.JUDGE: RolePolicyEntry(
            provider="deepseek", model=flash_model, temperature=0.2
        ),
        RolePolicy.VISION: RolePolicyEntry(
            provider="openai", model="gpt-5.6-luna", temperature=0.4
        ),
    }
```

`role_policy()` 메서드에서 flash 모델 바인딩:
```python
    def role_policy(self) -> RolePolicyConfig:
        """역할 정책을 반환한다. 미설정 시 기본값(flash 모델 통일) 사용."""
        if not self.role_policy_json.strip():
            return RolePolicyConfig(roles=_default_roles(self.deepseek_model_flash))
        raw = json.loads(self.role_policy_json)
        roles: dict[RolePolicy, RolePolicyEntry] = {}
        for role_str, entry in raw.items():
            role = RolePolicy(role_str)
            roles[role] = RolePolicyEntry.model_validate(entry)
        return RolePolicyConfig(roles=roles)
```

`errors.py` — ErrorCode에 추가:
```python
    # --- T07 다중 에이전트 ---
    AGENT_UNRESOLVED = "AGENT_UNRESOLVED"
    SCRIPT_REVIEW_REJECTED = "SCRIPT_REVIEW_REJECTED"
```

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/providers/test_settings_roles.py -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/math_variant/providers/contracts.py src/math_variant/providers/settings.py src/math_variant/errors.py tests/unit/providers/test_settings_roles.py
git commit -m "feat: add multi-agent role policy with flash/luna defaults"
```

---

## Task 2: 에이전트 응답 스키마 정의

**Files:**
- Create: `src/math_variant/agents/__init__.py`
- Create: `src/math_variant/agents/schemas.py`
- Create: `tests/unit/agents/test_schemas.py`

**Step 1: 실패 테스트 작성**

`tests/unit/agents/test_schemas.py`:
```python
"""T07 — 다중 에이전트 응답 스키마 불변식 테스트."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from math_variant.agents.schemas import (
    CodeReviewOutput,
    GeneratorOutput,
    IdeationOutput,
    JudgeOutput,
    PlannerOutput,
    SelectionOutput,
    VisionOutput,
    register_agent_schemas,
)
from math_variant.domain.transformation import Dimension
from math_variant.providers.registry import SchemaRegistry


def _planner(**overrides: object) -> dict:
    base = {
        "core_concepts": ["포물선", "평행이동", "직선"],
        "auxiliary_concepts": ["교점", "중점"],
        "objective": "중점이 주어진 직선 위에 있을 때 상수의 값을 구하시오",
        "answer_type": "expression",
        "domain": "이차함수·도형의 이동",
        "preservation_goals": ["평행이동 성질", "포물선과 직선의 교점"],
        "strategy": {
            "difficulty_target": "중상",
            "preservation_goals": ["평행이동 성질"],
            "variation_direction": ["질문 역전", "조건 일반화"],
            "quality_criteria": ["유일해", "범위 내 개념만"],
        },
        "unresolved_assumptions": [],
    }
    base.update(overrides)
    return base


def test_planner_schema_parses() -> None:
    output = PlannerOutput.model_validate(_planner())
    assert "포물선" in output.core_concepts
    assert output.strategy.difficulty_target == "중상"


def test_planner_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        PlannerOutput.model_validate(_planner(injected="extra"))


def test_ideation_dimension_coerces_from_string() -> None:
    data = {
        "idea_id": "idea-1",
        "title": "질문 역전",
        "preserved_concepts": ["평행이동"],
        "changed_dimensions": ["objective", "condition_topology"],
        "change_description": ["질문을 역전한다"],
        "construction_blueprint": "a를 주고 AB 길이를 구하게 한다",
        "figure_required": False,
    }
    output = IdeationOutput.model_validate(data)
    assert output.changed_dimensions == [Dimension.OBJECTIVE, Dimension.CONDITION_TOPOLOGY]


def test_generator_requires_verification_script() -> None:
    base = {
        "problem_text": "문제 본문",
        "formalization": {"symbols": ["x", "y"], "constraints": [], "goal": "a의 값"},
        "final_answer_claim": "8sqrt(2)",
        "solution_steps": [],
        "transformation_evidence": [],
    }
    with pytest.raises(ValidationError):
        GeneratorOutput.model_validate(base)
    output = GeneratorOutput.model_validate({**base, "verification_script": "result = {...}"})
    assert output.verification_script


def test_code_review_and_judge_schemas() -> None:
    review = CodeReviewOutput.model_validate(
        {"verdict": "APPROVE", "safe": True, "test_consistent": True, "feedback": ""}
    )
    assert review.verdict == "APPROVE"
    judge = JudgeOutput.model_validate(
        {"ranking": [{"candidate_id": "c1", "score": 8.0, "reason": "안전"}], "summary": ""}
    )
    assert judge.ranking[0]["candidate_id"] == "c1"


def test_vision_output_and_registry() -> None:
    vision = VisionOutput.model_validate({"tikz_code": r"\draw (0,0) -- (1,1);", "caption": ""})
    assert vision.tikz_code

    registry = SchemaRegistry()
    register_agent_schemas(registry)
    for name in ("PlannerOutput", "IdeationOutput", "SelectionOutput", "GeneratorOutput",
                 "CodeReviewOutput", "CriticOutput", "JudgeOutput", "VisionOutput"):
        assert name in registry._models
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/agents/test_schemas.py -v`
Expected: FAIL — `math_variant.agents.schemas` 모듈 없음.

**Step 3: 구현**

`src/math_variant/agents/__init__.py`:
```python
"""다중 에이전트 파이프라인 (T07)."""
```

`src/math_variant/agents/schemas.py`:
```python
"""다중 에이전트 응답 스키마 (T07).

모든 스키마는 extra="forbid" 로 LLM 응답의 추가 필드를 거부한다.
원문 본문은 PlannerOutput 에만 허용하고, IDEATOR/SELECTOR/GENERATOR 의
입력에는 원문 전문이 절대 포함되지 않는다 (원문 분리 원칙).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from math_variant.domain.candidate import Formalization, SolutionStepClaim
from math_variant.domain.transformation import Dimension
from math_variant.providers.registry import SchemaRegistry


class ProductionStrategy(BaseModel):
    """기획 단계에서 수립한 변형 전략 (원문 본문 없이 다음 단계로 전달된다)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    difficulty_target: str = Field(min_length=1)
    preservation_goals: list[str] = Field(min_length=1)
    variation_direction: list[str] = Field(min_length=1)
    quality_criteria: list[str] = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    """기획자 출력 — 원문 분석 + 변형 전략."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    core_concepts: list[str] = Field(min_length=1)
    auxiliary_concepts: list[str] = Field(default_factory=list)
    objective: str = Field(min_length=1)
    answer_type: str
    domain: str
    preservation_goals: list[str] = Field(min_length=1)
    strategy: ProductionStrategy
    unresolved_assumptions: list[str] = Field(default_factory=list)


class IdeationOutput(BaseModel):
    """발상자 출력 — 원문 없이 하나의 구조적 변형 아이디어."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    idea_id: str
    title: str = Field(min_length=1)
    preserved_concepts: list[str] = Field(min_length=1)
    changed_dimensions: list[Dimension] = Field(min_length=1)
    change_description: list[str] = Field(min_length=1)
    construction_blueprint: str = Field(min_length=1)
    figure_required: bool = False
    figure_notes: str = Field(default="")


class SelectionOutput(BaseModel):
    """선별자 출력 — 발상 아이디어 중 채택 목록."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    adopted_ideas: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class GeneratorOutput(BaseModel):
    """생성자 출력 — CandidateOutput + 검증 스크립트 + 도형 필요 여부."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    problem_text: str = Field(min_length=1)
    formalization: Formalization
    final_answer_claim: str = Field(min_length=1)
    solution_steps: list[SolutionStepClaim] = Field(default_factory=list)
    transformation_evidence: list[dict[str, Any]] = Field(default_factory=list)
    verification_script: str = Field(min_length=1)
    needs_figure: bool = False
    figure_notes: str = Field(default="")


class CodeReviewOutput(BaseModel):
    """검증 스크립트 심사자 출력."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    verdict: Literal["APPROVE", "REVISE", "REJECT"]
    safe: bool
    test_consistent: bool
    risk_notes: list[str] = Field(default_factory=list)
    feedback: str = Field(default="")

    @property
    def approves(self) -> bool:
        return self.verdict == "APPROVE"


class CriticOutput(BaseModel):
    """품질 비평가 출력."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    score: float = Field(ge=0, le=10)
    difficulty_estimate: str = Field(min_length=1)
    criteria_scores: dict[str, float] = Field(default_factory=dict)
    comments: list[str] = Field(default_factory=list)
    recommendation: Literal["PASS", "REVISE", "REJECT"] = "PASS"


class JudgeOutput(BaseModel):
    """최종 집계 출력 — 랭킹."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ranking: list[dict[str, Any]] = Field(min_length=1)
    summary: str = Field(default="")


class VisionOutput(BaseModel):
    """도형 렌더러 출력 — TikZ 코드."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tikz_code: str = Field(min_length=1)
    caption: str = Field(default="")


def register_agent_schemas(registry: SchemaRegistry) -> None:
    """에이전트 응답 스키마를 레지스트리에 등록한다."""
    for model in (
        PlannerOutput,
        IdeationOutput,
        SelectionOutput,
        GeneratorOutput,
        CodeReviewOutput,
        CriticOutput,
        JudgeOutput,
        VisionOutput,
    ):
        registry.register(model)
```

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/agents/test_schemas.py -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/math_variant/agents tests/unit/agents/test_schemas.py
git commit -m "feat: add multi-agent response schemas"
```

---

## Task 3: 에이전트 프롬프트 작성

**Files:**
- Create: `src/math_variant/prompts/planner.md`
- Create: `src/math_variant/prompts/ideator.md`
- Create: `src/math_variant/prompts/selector.md`
- Create: `src/math_variant/prompts/code_reviewer.md`
- Create: `src/math_variant/prompts/critic.md`
- Create: `src/math_variant/prompts/judge.md`
- Create: `src/math_variant/prompts/vision.md`
- Modify: `src/math_variant/prompts/candidate_generator.md`

**Step 1: 프롬프트 작성**

기존 `prompts/*.md`(blind_solver.md 등) 스타일을 따른다. 원문 분리 원칙을 각 프롬프트에 명시한다.

`planner.md`:
```markdown
# Planner 역할

당신은 수학 문항 변형 기획자입니다. 원문 본문을 분석하여 문제 구조(ProblemSpec)와
변형 전략을 수립합니다. 이 단계에서만 원문 본문을 볼 수 있습니다.

## 입력
- 정규화된 원문 본문
- 학교 범위 프로필 (exam_scope, 개념 어휘)

## 원칙
- 핵심 개념, 목표, 답 형태, 도메인을 구조화해 반환한다.
- 확정하지 못한 가정은 unresolved_assumptions 에 모두 남긴다 (fail-closed).
- 다음 단계(발상·선별·생성)는 원문을 보지 못한다. 변형 방향·보존 목표·품질 기준을
  스펙/전략으로 충분히 전달 가능하게 작성한다.

## 출력 스키마
- core_concepts, auxiliary_concepts, objective, answer_type, domain,
  preservation_goals, strategy{difficulty_target, preservation_goals,
  variation_direction, quality_criteria, constraints}, unresolved_assumptions
```

`ideator.md`:
```markdown
# Ideator 역할

당신은 수학 문항 변형 발상자입니다. 원문 본문은 받지 않습니다. 문제 구조 스펙과
변형 전략만 보고 창의적인 변형 아이디어를 하나 제안합니다. 다른 발상자와
겹치지 않도록 발산적으로 생각하십시오.

## 입력
- 문제 구조 스펙 (핵심 개념, 목표, 답 형태, 도메인)
- 변형 전략 (난이도 목표, 보존 목표, 변형 방향, 품질 기준)

## 원칙
- 원문 전체를 복사하거나 인용하지 않는다. 원문을 보지 않았으므로
  "원문 문항"이라는 문구 자체를 출력하지 않는다.
- 구조적 변경(질문 방향·조건 위상·풀이 경로·보조 구성)을 2개 이상 포함한다.
- 변형 차원(changed_dimensions)은 context/representation/data_domain 중 표면,
  objective/condition_topology/condition_order/auxiliary_construction/solution_route 중
  구조를 골라 4개 이상 제시한다.
- 단순 숫자 치환은 금지. 도형이 필요한 경우 figure_required=true 와 figure_notes 를 채운다.

## 출력 스키마
- idea_id, title, preserved_concepts, changed_dimensions, change_description,
  construction_blueprint, figure_required, figure_notes
```

`selector.md`:
```markdown
# Selector 역할

당신은 수학 문항 변형 아이디어 선별자입니다. 여러 발상자의 아이디어 중 변형 전략과
가장 잘 맞고, 교육적 가치와 검증 가능성이 높은 아이디어를 채택합니다.

## 입력
- 변형 전략 (난이도 목표, 보존 목표, 변형 방향, 품질 기준)
- 발상 아이디어 목록 (idea_id, title, changed_dimensions, blueprint)

## 원칙
- 채택은 최소 1개. 품질 기준과 어긋나는 아이디어(유일해 없음·범위 밖 개념)는 채택하지 않는다.
- 채택 근거(rationale)를 아이디어별로 요약한다.

## 출력 스키마
- adopted_ideas: 채택한 idea_id 배열
- rationale: 채택 근거
```

`code_reviewer.md`:
```markdown
# Code Reviewer 역할

당신은 검증 스크립트 심사자입니다. 생성기가 작성한 sympy 검증 테스트 스크립트를
두 축으로 평가합니다.

## 입력
- 문제 본문
- 주장 답 (final_answer_claim)
- 검증 스크립트 (Python, sympy 사용 가능)

## 평가 축
1. 위험성(safe): eval/exec, 파일/네트워크/호스트 접근, os/서브프로세스 남용,
   비밀 키 유사 문자열 → false. 루프·재귀 무한 반복 위험도 기록한다.
2. 테스트 정합성(test_consistent): 스크립트가 문제의 formalization 과 주장 답을
   실제로 검증하는지. 주장 답을 하드코딩해 PASS 를 돌려주는 "거짓 테스트"는 false.

## 판정
- APPROVE: 안전하고 정합적이다.
- REVISE: 문제가 있지만 고칠 여지가 있다 (feedback 에 구체적 수정 지시).
- REJECT: 폐기해야 한다 (feedback 에 이유).

## 출력 스키마
- verdict, safe, test_consistent, risk_notes, feedback
```

`critic.md`:
```markdown
# Critic 역할

당신은 수학 문항 품질 비평가입니다. 생성된 문제 후보를 난이도·참신성·명확성·교육
타당성 관점에서 평가합니다. 원문 본문은 받지 않으며 후보와 스펙·전략만 받습니다.

## 입력
- 문제 후보 본문, 주장 답, 풀이 단계
- 문제 구조 스펙, 변형 전략

## 원칙
- 난이도 정합성: 난이도 목표와 후보의 실질 난이도가 일치하는가.
- 참신성: 스펙·전략 대비 구조적으로 새로운가 (표면 치환이면 낮은 점수).
- 명확성: 조건·목표가 모호하지 않은가.
- 교육 타당성: 범위 내 개념만 사용하고 추측 요소가 없는가.

## 출력 스키마
- score(0~10), difficulty_estimate, criteria_scores{novelty, clarity, pedagogy,
  difficulty_consistency}, comments, recommendation(PASS|REVISE|REJECT)
```

`judge.md`:
```markdown
# Judge 역할

당신은 최종 집계자입니다. 검증 결과(테스트 실행 PASS 여부), 블라인드 합의,
품질 점수를 종합해 후보를 순위화합니다. 검증되지 않은 후보는 상위에 올 수 없습니다.

## 입력
- 후보별: candidate_id, problem_text, test_outcome(테스트 PASS 여부),
  blind_consensus(PASS/불일치), critic_score, code_review 결과

## 원칙
- 테스트 PASS + 블라인드 합의 + 높은 critic 점수를 우선한다.
- ranking 배열은 candidate_id, score(0~10), reason 로 구성한다.

## 출력 스키마
- ranking: [{candidate_id, score, reason}], summary
```

`vision.md`:
```markdown
# Vision 역할

당신은 수학 도형 TikZ 렌더러입니다. 문제 설명(figure_notes)과 후보 본문을 보고
LaTeX TikZ 코드를 생성합니다. 정확하고 컴파일 가능한 코드만 반환합니다.

## 원칙
- 시각 정보(좌표축, 포물선, 직선, 교점, 중점 표시)만 그리고, 해답 표기는 하지 않는다.
- 사용자 정의 매크로 없이 표준 TikZ만 사용한다.

## 출력 스키마
- tikz_code, caption
```

`candidate_generator.md` 수정(끝에 추가):
```markdown
## 검증 스크립트
- verification_script: 문제의 주장 답(final_answer_claim)을 sympy 로 독립 검증하는
  Python 스크립트를 작성한다. 다음 계약을 지킨다.
  - 마지막에 `result = {"verdict": "PASS", "detail": "..."}` 로 끝나야 한다.
  - 실패하면 예외를 던지거나 verdict 를 "FAIL" 로 설정한다.
  - 주장 답을 그대로 하드코딩해 PASS 를 돌려주는 거짓 테스트는 금지다.
  - eval/exec, 파일·네트워크·호스트 접근, os.environ, 비밀 키 문자열은 금지다.
  - 문제에 도형/그림이 필요하면 needs_figure=true, figure_notes 를 채운다.
```

**Step 2: 파일 존재 확인**

Run: `Get-ChildItem src/math_variant/prompts | Select-Object Name`
Expected: planner.md, ideator.md, selector.md, code_reviewer.md, critic.md, judge.md, vision.md 포함.

**Step 3: 커밋**

```bash
git add src/math_variant/prompts
git commit -m "feat: add multi-agent prompt bundles with source-isolation rules"
```

---

## Task 4: 검증 테스트 스크립트 러너

**Files:**
- Create: `src/math_variant/verifiers/test_runner.py`
- Create: `tests/unit/verifiers/test_test_runner.py`

**Step 1: 실패 테스트 작성**

`tests/unit/verifiers/test_test_runner.py`:
```python
"""T07 — 검증 테스트 스크립트 러너 판정 테스트."""

from __future__ import annotations

import pytest

from math_variant.sandbox.contracts import SandboxResult, SandboxStatus
from math_variant.verifiers.test_runner import (
    TestVerdict,
    VerificationOutcome,
    build_verification_request,
    interpret,
)


def _result(status: SandboxStatus, output: dict | None = None, stderr: str = "") -> SandboxResult:
    return SandboxResult(
        result_id="r",
        request_id="req",
        status=status,
        output_json=output,
        stderr=stderr,
        duration_ms=10,
        image_digest="sha256:abc",
    )


def test_completed_with_pass_verdict_is_pass() -> None:
    outcome = interpret(_result(SandboxStatus.COMPLETED, {"result": {"verdict": "PASS"}}))
    assert outcome.verdict == TestVerdict.PASS


def test_completed_without_pass_verdict_is_fail() -> None:
    outcome = interpret(_result(SandboxStatus.COMPLETED, {"result": {"verdict": "FAIL"}}))
    assert outcome.verdict == TestVerdict.FAIL
    outcome2 = interpret(_result(SandboxStatus.COMPLETED, {"result": 42}))
    assert outcome2.verdict == TestVerdict.FAIL


def test_code_error_and_timeout_are_fail() -> None:
    assert interpret(_result(SandboxStatus.CODE_ERROR, stderr="ZeroDivisionError")).verdict == TestVerdict.FAIL
    assert interpret(_result(SandboxStatus.TIMEOUT)).verdict == TestVerdict.FAIL


def test_policy_and_infra_are_unresolved() -> None:
    assert interpret(_result(SandboxStatus.POLICY_VIOLATION, stderr="금지 패턴")).verdict == TestVerdict.UNRESOLVED
    assert interpret(_result(SandboxStatus.INFRA_ERROR)).verdict == TestVerdict.UNRESOLVED


def test_build_request_embeds_script_and_context() -> None:
    request = build_verification_request(
        "req-1",
        "from sympy import symbols\nresult = {'verdict': 'PASS'}",
        {"problem": "x=1"},
    )
    assert request.code.startswith("from sympy")
    assert request.input_json == {"problem": "x=1"}
    assert "sympy" in request.allowed_packages
    assert request.resource_budget.cpu_seconds == 20


def test_outcome_is_frozen() -> None:
    outcome = VerificationOutcome(verdict=TestVerdict.PASS, status=SandboxStatus.COMPLETED)
    with pytest.raises(Exception):
        outcome.verdict = TestVerdict.FAIL  # type: ignore[misc]
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/verifiers/test_test_runner.py -v`
Expected: FAIL — 모듈 없음.

**Step 3: 구현**

`src/math_variant/verifiers/test_runner.py`:
```python
"""검증 테스트 스크립트 러너 (T07).

생성기가 작성한 sympy 검증 스크립트를 샌드박스 공급자에서 실행하고
결정론적으로 PASS/FAIL/UNRESOLVED 를 판정한다.

스크립트 계약 (candidate_generator.md 참고):
- 전체 Python 스크립트로 sympy·math 등을 import 할 수 있다.
- 마지막에 `result = {"verdict": "PASS", "detail": "..."}` 를 설정해야 한다.
- 실패는 예외를 던지거나 result["verdict"] 를 "FAIL" 로 설정해 표현한다.
- 실행기(infra/sandbox/runner.py)는 `exec(code, sandbox_globals, data)` 로 실행하고
  스크립트가 설정한 `result` 를 output_json["result"] 로 반환한다.

판정은 스크립트 결과를 신뢰하지 않는다:
- COMPLETED + result.verdict == "PASS" 만 PASS.
- 그 외(실패/시간초과/거짓 결과/정책 위반/인프라 오류)는 FAIL 또는 UNRESOLVED.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from math_variant.sandbox.contracts import (
    ResourceBudget,
    SandboxRequest,
    SandboxResult,
    SandboxStatus,
)
from math_variant.sandbox.provider import SandboxProvider


class TestVerdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNRESOLVED = "UNRESOLVED"


class VerificationOutcome(BaseModel):
    """검증 스크립트 실행 판정 결과."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    verdict: TestVerdict
    status: SandboxStatus
    detail: str = ""
    duration_ms: int = 0
    image_digest: str | None = None

    @property
    def passes(self) -> bool:
        return self.verdict == TestVerdict.PASS


def build_verification_request(
    request_id: str,
    verification_script: str,
    problem_context: dict[str, Any],
) -> SandboxRequest:
    """검증 스크립트를 샌드박스 요청으로 감싼다."""
    return SandboxRequest(
        request_id=request_id,
        code=verification_script,
        input_json=problem_context,
        allowed_packages=["sympy", "mpmath", "math", "fractions", "itertools", "collections"],
        resource_budget=ResourceBudget(cpu_seconds=20, max_output_chars=20000),
        expected_output_schema="verification_verdict",
    )


def run_verification(provider: SandboxProvider, request: SandboxRequest) -> VerificationOutcome:
    """샌드박스 공급자에서 검증 스크립트를 실행하고 판정한다."""
    return interpret(provider.execute(request))


def interpret(result: SandboxResult) -> VerificationOutcome:
    """샌드박스 실행 결과를 결정론적으로 판정한다."""
    if result.status == SandboxStatus.POLICY_VIOLATION:
        return VerificationOutcome(
            verdict=TestVerdict.UNRESOLVED,
            status=result.status,
            detail=result.stderr[:500],
            duration_ms=result.duration_ms,
        )
    if result.status == SandboxStatus.INFRA_ERROR:
        return VerificationOutcome(
            verdict=TestVerdict.UNRESOLVED,
            status=result.status,
            detail=result.stderr[:500],
            duration_ms=result.duration_ms,
        )
    if result.status == SandboxStatus.TIMEOUT:
        return VerificationOutcome(
            verdict=TestVerdict.FAIL,
            status=result.status,
            detail="검증 스크립트 실행 시간 초과",
            duration_ms=result.duration_ms,
        )
    if result.status == SandboxStatus.CODE_ERROR:
        return VerificationOutcome(
            verdict=TestVerdict.FAIL,
            status=result.status,
            detail=result.stderr[:500],
            duration_ms=result.duration_ms,
        )
    payload = result.output_json or {}
    inner = payload.get("result")
    if isinstance(inner, dict) and inner.get("verdict") == "PASS":
        return VerificationOutcome(
            verdict=TestVerdict.PASS,
            status=result.status,
            detail=str(inner.get("detail", ""))[:500],
            duration_ms=result.duration_ms,
            image_digest=result.image_digest,
        )
    return VerificationOutcome(
        verdict=TestVerdict.FAIL,
        status=result.status,
        detail=f"검증 스크립트가 PASS 를 반환하지 않았다: {inner!r}"[:500],
        duration_ms=result.duration_ms,
    )
```

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/verifiers/test_test_runner.py -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/math_variant/verifiers/test_runner.py tests/unit/verifiers/test_test_runner.py
git commit -m "feat: add sandbox verification script runner"
```

---

## Task 5: 에이전트 서비스 구현 (planner/ideator/selector)

**Files:**
- Create: `src/math_variant/agents/planner.py`
- Create: `src/math_variant/agents/ideator.py`
- Create: `src/math_variant/agents/selector.py`
- Create: `src/math_variant/agents/_common.py`
- Create: `tests/unit/agents/test_planner_ideator_selector.py`

**Step 1: 실패 테스트 작성**

`tests/unit/agents/test_planner_ideator_selector.py`:
```python
"""T07 — 기획·발상·선별 에이전트 테스트."""

from __future__ import annotations

import pytest

from math_variant.agents.ideator import IdeatorAgent, build_ideation_brief
from math_variant.agents.planner import PlannerAgent
from math_variant.agents.selector import SelectorAgent
from math_variant.agents.schemas import IdeationOutput, PlannerOutput, SelectionOutput
from math_variant.errors import MathVariantError
from math_variant.providers.contracts import ProviderResponse, RolePolicy
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine

_PLANNER_DATA = {
    "core_concepts": ["포물선", "평행이동", "직선"],
    "auxiliary_concepts": ["교점", "중점"],
    "objective": "상수의 값과 길이의 곱을 구하시오",
    "answer_type": "expression",
    "domain": "이차함수·도형의 이동",
    "preservation_goals": ["평행이동 성질", "교점·중점"],
    "strategy": {
        "difficulty_target": "중상",
        "preservation_goals": ["평행이동 성질"],
        "variation_direction": ["질문 역전", "조건 일반화"],
        "quality_criteria": ["유일해", "범위 내 개념"],
    },
    "unresolved_assumptions": [],
}

_IDEA = {
    "idea_id": "idea-1",
    "title": "질문 역전",
    "preserved_concepts": ["평행이동"],
    "changed_dimensions": ["objective", "condition_topology", "solution_route", "data_domain"],
    "change_description": ["질문을 역전한다"],
    "construction_blueprint": "a를 주고 조건을 만족하는 값을 구하게 한다",
}


class _Engine(StructuredOutputEngine):
    """역할별 고정 응답을 주입하는 테스트 엔진."""

    def __init__(self, data: dict, roles: set[str]) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self._data = data
        self._roles = roles
        self.calls: list[RolePolicy] = []

    def generate_structured(self, request, policy=None) -> ProviderResponse:
        self.calls.append(request.role)
        if request.role.value not in self._roles:
            raise AssertionError(f"예상치 못한 역할: {request.role}")
        return ProviderResponse(request_id=request.request_id, ok=True, data=self._data)


def test_planner_returns_strategy_and_rejects_original_text_in_strategy() -> None:
    engine = _Engine(_PLANNER_DATA, {"planner"})
    agent = PlannerAgent(engine=engine, prompt_bundle="기획 프롬프트")
    output = agent.plan("포물선 y=x^2-3x-8 을 평행이동 ...")

    assert isinstance(output, PlannerOutput)
    assert engine.calls == [RolePolicy.PLANNER]
    serialized = output.model_dump_json()
    assert "y=x^2-3x-8" not in serialized


def test_planner_engine_failure_raises() -> None:
    class Broken(_Engine):
        def generate_structured(self, request, policy=None) -> ProviderResponse:
            return ProviderResponse(request_id=request.request_id, ok=False)

    agent = PlannerAgent(engine=Broken(_PLANNER_DATA, {"planner"}), prompt_bundle="p")
    with pytest.raises(MathVariantError) as exc_info:
        agent.plan("원문")
    assert exc_info.value.code == "AGENT_UNRESOLVED"


def test_ideator_uses_high_temperature_role_and_never_sees_original() -> None:
    engine = _Engine(_IDEA, {"ideator"})
    agent = IdeatorAgent(engine=engine, prompt_bundle="발상 프롬프트")
    brief = build_ideation_brief(
        core_concepts=["포물선", "평행이동"],
        objective="상수의 값과 길이의 곱을 구하시오",
        answer_type="expression",
        domain="이차함수·도형의 이동",
        preservation_goals=["평행이동 성질"],
        strategy=_PLANNER_DATA["strategy"],  # type: ignore[arg-type]
    )
    assert "y=x^2" not in brief
    idea = agent.ideate(brief, seed="a")
    assert isinstance(idea, IdeationOutput)


def test_selector_adopts_ideas() -> None:
    engine = _Engine(
        {"adopted_ideas": ["idea-1", "idea-3"], "rationale": "전략 부합"},
        {"selector"},
    )
    agent = SelectorAgent(engine=engine, prompt_bundle="선별 프롬프트")
    ideas = [IdeationOutput.model_validate({**_IDEA, "idea_id": f"idea-{i}"}) for i in (1, 2, 3)]
    output = agent.select(ideas)
    assert isinstance(output, SelectionOutput)
    assert output.adopted_ideas == ["idea-1", "idea-3"]
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/agents/test_planner_ideator_selector.py -v`
Expected: FAIL — 모듈 없음.

**Step 3: 구현**

`src/math_variant/agents/_common.py`:
```python
"""에이전트 공통 헬퍼 — 구조화 요청 실행과 실패 처리."""

from __future__ import annotations

from math_variant.errors import ErrorCode, MathVariantError, StructuredError
from math_variant.providers.contracts import RolePolicy, StructuredRequest
from math_variant.providers.structured import StructuredOutputEngine


def request_structured(
    engine: StructuredOutputEngine,
    request_id: str,
    role: RolePolicy,
    prompt: str,
    schema: str,
) -> dict:
    """구조화 요청을 실행하고 실패를 AGENT_UNRESOLVED 로 변환한다."""
    response = engine.generate_structured(
        StructuredRequest(
            request_id=request_id,
            role=role,
            prompt=prompt,
            response_schema=schema,
        ),
        policy=None,
    )
    if not response.ok or response.data is None:
        raise MathVariantError(
            StructuredError(
                code=ErrorCode.AGENT_UNRESOLVED,
                message=f"에이전트({role.value})가 구조화된 응답을 생성하지 못했다",
                context={"provider_error": response.error.model_dump() if response.error else None},
            )
        )
    return response.data
```

`src/math_variant/agents/planner.py`:
```python
"""기획자 에이전트 — 원문 분석 + 변형 전략 수립 (T07).

원문 본문은 이 에이전트에서만 소비된다. 이후 단계에는 PlannerOutput(스펙·전략)만 전달한다.
"""

from __future__ import annotations

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import PlannerOutput
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


class PlannerAgent:
    """PLANNER 역할을 호출해 원문 스펙·전략을 추출한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle

    def plan(self, source_text: str) -> PlannerOutput:
        prompt = f"{self.prompt_bundle}\n\n[원문]\n{source_text}"
        data = request_structured(
            self.engine,
            request_id="planner",
            role=RolePolicy.PLANNER,
            prompt=prompt,
            schema="PlannerOutput",
        )
        return PlannerOutput.model_validate(data)
```

`src/math_variant/agents/ideator.py`:
```python
"""발상자 에이전트 — 원문 없이 구조적 변형 아이디어 제안 (T07).

입력에는 원문 본문이 절대 포함되지 않는다. 높은 temperature(1.4) 로 발산을 유도한다.
"""

from __future__ import annotations

from typing import Any

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import IdeationOutput
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


def build_ideation_brief(
    *,
    core_concepts: list[str],
    objective: str,
    answer_type: str,
    domain: str,
    preservation_goals: list[str],
    strategy: dict[str, Any],
) -> str:
    """스펙·전략만 담은 발상 입력 브리프를 만든다 (원문 본문 없음)."""
    return (
        "[문제 구조]\n"
        f"- 핵심 개념: {core_concepts}\n"
        f"- 목표: {objective}\n"
        f"- 답 형태: {answer_type}\n"
        f"- 도메인: {domain}\n"
        f"- 보존 목표: {preservation_goals}\n"
        "[변형 전략]\n"
        f"- 난이도 목표: {strategy.get('difficulty_target')}\n"
        f"- 변형 방향: {strategy.get('variation_direction')}\n"
        f"- 품질 기준: {strategy.get('quality_criteria')}\n"
        f"- 제약: {strategy.get('constraints')}"
    )


class IdeatorAgent:
    """IDEATOR 역할을 호출해 변형 아이디어 하나를 생산한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle

    def ideate(self, brief: str, seed: str) -> IdeationOutput:
        prompt = f"{self.prompt_bundle}\n\n[입력]\n{brief}"
        data = request_structured(
            self.engine,
            request_id=f"ideator-{seed}",
            role=RolePolicy.IDEATOR,
            prompt=prompt,
            schema="IdeationOutput",
        )
        return IdeationOutput.model_validate(data)
```

`src/math_variant/agents/selector.py`:
```python
"""선별자 에이전트 — 발상 아이디어 채택 (T07)."""

from __future__ import annotations

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import IdeationOutput, SelectionOutput
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


class SelectorAgent:
    """SELECTOR 역할을 호출해 채택 아이디어를 결정한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle

    def select(self, ideas: list[IdeationOutput], strategy_brief: str) -> SelectionOutput:
        listing = "\n".join(f"- {i.idea_id}: {i.title} | {i.construction_blueprint}" for i in ideas)
        prompt = (
            f"{self.prompt_bundle}\n\n[변형 전략]\n{strategy_brief}\n\n[아이디어 목록]\n{listing}"
        )
        data = request_structured(
            self.engine,
            request_id="selector",
            role=RolePolicy.SELECTOR,
            prompt=prompt,
            schema="SelectionOutput",
        )
        return SelectionOutput.model_validate(data)
```

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/agents/test_planner_ideator_selector.py -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/math_variant/agents tests/unit/agents/test_planner_ideator_selector.py
git commit -m "feat: add planner/ideator/selector agents"
```

---

## Task 6: 생성·코드리뷰·비평·집계·도형 에이전트 구현

**Files:**
- Create: `src/math_variant/agents/generator.py`
- Create: `src/math_variant/agents/code_reviewer.py`
- Create: `src/math_variant/agents/critic.py`
- Create: `src/math_variant/agents/judge.py`
- Create: `src/math_variant/agents/vision_artist.py`
- Create: `tests/unit/agents/test_generator_and_verifiers.py`

**Step 1: 실패 테스트 작성**

`tests/unit/agents/test_generator_and_verifiers.py`:
```python
"""T07 — 생성·코드리뷰·비평·집계·도형 에이전트 테스트."""

from __future__ import annotations

import pytest

from math_variant.agents.code_reviewer import CodeReviewAgent
from math_variant.agents.critic import CriticAgent
from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.judge import JudgeAgent
from math_variant.agents.schemas import (
    CodeReviewOutput,
    CriticOutput,
    GeneratorOutput,
    JudgeOutput,
)
from math_variant.agents.vision_artist import VisionArtist
from math_variant.domain.candidate import CandidateProblem
from math_variant.providers.contracts import ProviderResponse, RolePolicy
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine

_BLUEPRINT = {
    "title": "질문 역전",
    "preserved_concepts": ["평행이동"],
    "changed_dimensions": ["objective", "condition_topology", "solution_route", "data_domain"],
    "change_description": ["질문을 역전한다"],
    "construction_blueprint": "a를 주고 조건을 만족하는 값을 구하게 한다",
}

_CANDIDATE = {
    "problem_text": "포물선 y=(x-2)^2-1 과 직선 y=x 가 서로 다른 두 점에서 만난다...",
    "formalization": {"symbols": ["x", "a"], "constraints": [], "goal": "a의 값"},
    "final_answer_claim": "8sqrt(2)",
    "solution_steps": [{"step_id": "s1", "statement": "대입 후 판별식"}],
    "transformation_evidence": [{"dimension": "objective", "description": "역전"}],
    "verification_script": "from sympy import symbols\nresult = {'verdict': 'PASS'}",
    "needs_figure": True,
    "figure_notes": "포물선과 직선, 교점 A, B 표시",
}

_REVIEW = {"verdict": "APPROVE", "safe": True, "test_consistent": True, "feedback": ""}
_CRITIC = {
    "score": 8.0,
    "difficulty_estimate": "중상",
    "criteria_scores": {"novelty": 8, "clarity": 9, "pedagogy": 8, "difficulty_consistency": 7},
    "comments": ["구조적 변형이 충분하다"],
    "recommendation": "PASS",
}
_JUDGE = {
    "ranking": [{"candidate_id": "c1", "score": 8.0, "reason": "검증 통과"}],
    "summary": "1건 채택",
}


class _Engine(StructuredOutputEngine):
    def __init__(self, data: dict, roles: set[str]) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self._data = data
        self._roles = roles
        self.calls: list[RolePolicy] = []

    def generate_structured(self, request, policy=None) -> ProviderResponse:
        self.calls.append(request.role)
        assert request.role.value in self._roles
        return ProviderResponse(request_id=request.request_id, ok=True, data=self._data)


def test_generator_assembles_candidate_with_script() -> None:
    engine = _Engine(_CANDIDATE, {"generator"})
    agent = GeneratorAgent(engine=engine, prompt_bundle="생성 프롬프트")
    candidate, extra = agent.generate(
        candidate_id="cand-1", blueprint=_BLUEPRINT, brief="브리프"
    )
    assert isinstance(candidate, CandidateProblem)
    assert extra.verification_script.startswith("from sympy")
    assert extra.needs_figure is True
    assert engine.calls == [RolePolicy.GENERATOR]


def test_generator_refine_includes_feedback_in_prompt() -> None:
    engine = _Engine(_CANDIDATE, {"generator"})
    agent = GeneratorAgent(engine=engine, prompt_bundle="생성 프롬프트")
    agent.generate(candidate_id="cand-2", blueprint=_BLUEPRINT, brief="브리프",
                   feedback="검증 스크립트가 거짓 테스트다")
    assert "검증 스크립트가 거짓 테스트다" in agent._last_prompt


def test_code_reviewer_returns_review() -> None:
    engine = _Engine(_REVIEW, {"code_reviewer"})
    agent = CodeReviewAgent(engine=engine, prompt_bundle="심사 프롬프트")
    review = agent.review("script", "문제 본문", "8sqrt(2)")
    assert isinstance(review, CodeReviewOutput)
    assert review.approves


def test_critic_and_judge() -> None:
    engine = _Engine(_CRITIC, {"critic"})
    critic = CriticAgent(engine=engine, prompt_bundle="비평 프롬프트")
    assert isinstance(critic.criticize("문제", "스펙", "전략"), CriticOutput)

    engine_j = _Engine(_JUDGE, {"judge"})
    judge = JudgeAgent(engine=engine_j, prompt_bundle="집계 프롬프트")
    assert isinstance(judge.judge([{"candidate_id": "c1", "score": 8.0}]), JudgeOutput)


def test_vision_artist_writes_tikz(tmp_path) -> None:
    engine = _Engine({"tikz_code": r"\draw (0,0) -- (1,1);", "caption": "포물선"}, {"vision"})
    artist = VisionArtist(engine=engine, prompt_bundle="도형 프롬프트", figures_dir=tmp_path)
    path = artist.render("cand-1", figure_notes="포물선과 직선")
    assert path.name == "cand-1.tex"
    assert path.read_text(encoding="utf-8").startswith("%")
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/agents/test_generator_and_verifiers.py -v`
Expected: FAIL — 모듈 없음.

**Step 3: 구현**

`src/math_variant/agents/generator.py`:
```python
"""생성자 에이전트 — 청사진·스펙만으로 문제 + 검증 스크립트 생성 (T07)."""

from __future__ import annotations

from typing import Any

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import GeneratorOutput
from math_variant.domain.candidate import CandidateProblem
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


class GeneratorAgent:
    """GENERATOR 역할을 호출해 후보 문제와 검증 스크립트를 생산한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle
        self._last_prompt = ""

    def generate(
        self,
        candidate_id: str,
        blueprint: dict[str, Any],
        brief: str,
        feedback: str = "",
    ) -> tuple[CandidateProblem, GeneratorOutput]:
        self._last_prompt = self._build_prompt(blueprint, brief, feedback)
        data = request_structured(
            self.engine,
            request_id=candidate_id,
            role=RolePolicy.GENERATOR,
            prompt=self._last_prompt,
            schema="GeneratorOutput",
        )
        output = GeneratorOutput.model_validate(data)
        candidate = CandidateProblem(
            candidate_id=candidate_id,
            plan_id=f"plan-{blueprint.get('title', 'llm')}",
            problem_text=output.problem_text,
            formalization=output.formalization,
            final_answer_claim=output.final_answer_claim,
            solution_steps=output.solution_steps,
            transformation_evidence=output.transformation_evidence,
        )
        return candidate, output

    def _build_prompt(self, blueprint: dict[str, Any], brief: str, feedback: str) -> str:
        prompt = (
            f"{self.prompt_bundle}\n\n"
            f"[문제 구조]\n{brief}\n"
            f"[승인 청사진]\n"
            f"- 보존: {blueprint.get('preserved_concepts')}\n"
            f"- 변경 차원: {blueprint.get('changed_dimensions')}\n"
            f"- 구성 청사진: {blueprint.get('construction_blueprint')}\n"
        )
        if feedback.strip():
            prompt += f"[수정 지시]\n{feedback}\n"
        return prompt
```

`src/math_variant/agents/code_reviewer.py`:
```python
"""검증 스크립트 심사자 — 위험성·정합성 평가 (T07)."""

from __future__ import annotations

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import CodeReviewOutput
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


class CodeReviewAgent:
    """CODE_REVIEWER 역할을 호출해 검증 스크립트를 심사한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle

    def review(self, verification_script: str, problem_text: str, claimed_answer: str) -> CodeReviewOutput:
        prompt = (
            f"{self.prompt_bundle}\n\n"
            f"[문제 본문]\n{problem_text}\n"
            f"[주장 답]\n{claimed_answer}\n"
            f"[검증 스크립트]\n```python\n{verification_script}\n```"
        )
        data = request_structured(
            self.engine,
            request_id="code-review",
            role=RolePolicy.CODE_REVIEWER,
            prompt=prompt,
            schema="CodeReviewOutput",
        )
        return CodeReviewOutput.model_validate(data)
```

`src/math_variant/agents/critic.py`:
```python
"""품질 비평가 — 난이도·참신성·명확성·교육 타당성 평가 (T07)."""

from __future__ import annotations

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import CriticOutput
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


class CriticAgent:
    """CRITIC 역할을 호출해 후보 품질을 평가한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle

    def criticize(self, problem_text: str, spec_brief: str, strategy_brief: str) -> CriticOutput:
        prompt = (
            f"{self.prompt_bundle}\n\n"
            f"[문제 후보]\n{problem_text}\n"
            f"[문제 구조]\n{spec_brief}\n"
            f"[변형 전략]\n{strategy_brief}"
        )
        data = request_structured(
            self.engine,
            request_id="critic",
            role=RolePolicy.CRITIC,
            prompt=prompt,
            schema="CriticOutput",
        )
        return CriticOutput.model_validate(data)
```

`src/math_variant/agents/judge.py`:
```python
"""최종 집계자 — 검증·합의·품질 종합 순위화 (T07)."""

from __future__ import annotations

import json
from typing import Any

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import JudgeOutput
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


class JudgeAgent:
    """JUDGE 역할을 호출해 후보 랭킹을 산출한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle

    def judge(self, entries: list[dict[str, Any]]) -> JudgeOutput:
        prompt = (
            f"{self.prompt_bundle}\n\n"
            f"[후보 검증 결과]\n{json.dumps(entries, ensure_ascii=False, indent=2)}"
        )
        data = request_structured(
            self.engine,
            request_id="judge",
            role=RolePolicy.JUDGE,
            prompt=prompt,
            schema="JudgeOutput",
        )
        return JudgeOutput.model_validate(data)
```

`src/math_variant/agents/vision_artist.py`:
```python
"""도형 렌더러 — VISION(gpt-5.6-luna)으로 TikZ 코드를 생성해 파일로 저장한다 (T07)."""

from __future__ import annotations

from pathlib import Path

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import VisionOutput
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine


class VisionArtist:
    """VISION 역할을 호출해 후보의 도형을 TikZ 로 렌더링한다."""

    def __init__(
        self, engine: StructuredOutputEngine, prompt_bundle: str, figures_dir: Path
    ) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle
        self.figures_dir = figures_dir

    def render(self, candidate_id: str, figure_notes: str, problem_text: str = "") -> Path:
        prompt = (
            f"{self.prompt_bundle}\n\n"
            f"[문제 본문]\n{problem_text}\n"
            f"[도형 설명]\n{figure_notes}"
        )
        data = request_structured(
            self.engine,
            request_id=f"vision-{candidate_id}",
            role=RolePolicy.VISION,
            prompt=prompt,
            schema="VisionOutput",
        )
        output = VisionOutput.model_validate(data)
        return self._save(candidate_id, output)

    def _save(self, candidate_id: str, output: VisionOutput) -> Path:
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        path = self.figures_dir / f"{candidate_id}.tex"
        body = output.tikz_code.strip().strip("`")
        path.write_text(f"% figure for {candidate_id}\n% {output.caption}\n{body}\n", encoding="utf-8")
        return path
```

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/agents/test_generator_and_verifiers.py -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/math_variant/agents tests/unit/agents/test_generator_and_verifiers.py
git commit -m "feat: add generator/code-review/critic/judge/vision agents"
```

---

## Task 7: 파이프라인 오케스트레이터 (병렬 + 개선 루프 + 판정)

**Files:**
- Create: `src/math_variant/agents/pipeline.py`
- Create: `src/math_variant/agents/blind.py`
- Create: `tests/unit/agents/test_pipeline.py`

**Step 1: 실패 테스트 작성**

`tests/unit/agents/test_pipeline.py`:
```python
"""T07 — 파이프라인 오케스트레이터 테스트 (병렬·게이트·개선 루프)."""

from __future__ import annotations

from pathlib import Path

from math_variant.agents.code_reviewer import CodeReviewAgent
from math_variant.agents.critic import CriticAgent
from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.ideator import IdeatorAgent
from math_variant.agents.judge import JudgeAgent
from math_variant.agents.pipeline import AgentPipeline
from math_variant.agents.planner import PlannerAgent
from math_variant.agents.schemas import (
    CodeReviewOutput,
    CriticOutput,
    GeneratorOutput,
    IdeationOutput,
    JudgeOutput,
    PlannerOutput,
    SelectionOutput,
)
from math_variant.agents.selector import SelectorAgent
from math_variant.providers.contracts import ProviderResponse, RolePolicy
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine
from math_variant.sandbox.contracts import SandboxResult, SandboxStatus
from math_variant.services.blind_solver import BlindConsensus, BlindSolution

_PLANNER = {
    "core_concepts": ["포물선", "평행이동", "직선"],
    "auxiliary_concepts": ["교점", "중점"],
    "objective": "상수의 값과 길이의 곱을 구하시오",
    "answer_type": "expression",
    "domain": "이차함수·도형의 이동",
    "preservation_goals": ["평행이동 성질"],
    "strategy": {
        "difficulty_target": "중상",
        "preservation_goals": ["평행이동 성질"],
        "variation_direction": ["질문 역전"],
        "quality_criteria": ["유일해"],
    },
    "unresolved_assumptions": [],
}

_IDEAS = [
    {
        "idea_id": "idea-1",
        "title": "질문 역전",
        "preserved_concepts": ["평행이동"],
        "changed_dimensions": ["objective", "condition_topology", "solution_route", "data_domain"],
        "change_description": ["질문 역전"],
        "construction_blueprint": "중점 조건을 이용해 a를 구한다",
    },
    {
        "idea_id": "idea-2",
        "title": "직선 일반화",
        "preserved_concepts": ["평행이동", "교점"],
        "changed_dimensions": ["condition_topology", "data_domain", "objective", "solution_route"],
        "change_description": ["직선을 y=x+k 로 일반화"],
        "construction_blueprint": "직선 기울기를 매개화해 교점 조건을 바꾼다",
    },
]

_CANDIDATE = {
    "problem_text": "포물선 y=(x-2)^2-1 과 직선 y=x 가 서로 다른 두 점 A, B 에서 만난다. 중점이 x=3 위에 있을 때 a의 값과 AB 길이의 곱을 구하시오.",
    "formalization": {"symbols": ["x", "a"], "constraints": [], "goal": "a의 값"},
    "final_answer_claim": "8sqrt(2)",
    "solution_steps": [{"step_id": "s1", "statement": "대입"}],
    "transformation_evidence": [{"dimension": "objective", "description": "역전"}],
    "verification_script": "result = {'verdict': 'PASS'}",
}

_REVIEW_OK = {"verdict": "APPROVE", "safe": True, "test_consistent": True, "feedback": ""}
_REVIEW_REVISE = {"verdict": "REVISE", "safe": True, "test_consistent": False,
                  "feedback": "검증 스크립트가 답을 검증하지 않는다"}
_CRITIC = {
    "score": 8.0,
    "difficulty_estimate": "중상",
    "criteria_scores": {"novelty": 8, "clarity": 9, "pedagogy": 8, "difficulty_consistency": 7},
    "comments": [],
    "recommendation": "PASS",
}
_JUDGE = {
    "ranking": [{"candidate_id": "cand-1", "score": 8.0, "reason": "검증 통과"}],
    "summary": "채택",
}


class _Engine(StructuredOutputEngine):
    """역할별 응답을 순차 큐로 주입하는 테스트 엔진."""

    def __init__(self, responses: dict[str, list[dict]]) -> None:
        super().__init__(primary=None, fallback=None, schemas=SchemaRegistry())
        self.responses = {k: list(v) for k, v in responses.items()}
        self.calls: list[tuple[RolePolicy, str]] = []

    def generate_structured(self, request, policy=None) -> ProviderResponse:
        self.calls.append((request.role, request.prompt))
        queue = self.responses.get(request.role.value, [])
        if not queue:
            return ProviderResponse(request_id=request.request_id, ok=False)
        data = queue.pop(0)
        return ProviderResponse(request_id=request.request_id, ok=True, data=data)


class _PassSandbox:
    name = "fake"

    def execute(self, request) -> SandboxResult:
        return SandboxResult(
            result_id="r", request_id=request.request_id,
            status=SandboxStatus.COMPLETED,
            output_json={"result": {"verdict": "PASS"}},
        )


class _PassSolvers:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def solve_both(self, problem_text: str) -> BlindConsensus:
        self.calls.append(problem_text)
        return BlindConsensus(status="PASS", solver_a="A", solver_b="B", reason="동치")


def _build_engine() -> _Engine:
    return _Engine({
        "planner": [_PLANNER],
        "ideator": [_IDEAS[0], _IDEAS[1]],
        "selector": [{"adopted_ideas": ["idea-1", "idea-2"], "rationale": "부합"}],
        "generator": [_CANDIDATE, _CANDIDATE],
        "code_reviewer": [_REVIEW_OK, _REVIEW_OK],
        "critic": [_CRITIC, _CRITIC],
        "judge": [_JUDGE],
    })


def _pipeline(engine: _Engine, tmp_path: Path, max_refine: int = 1) -> AgentPipeline:
    return AgentPipeline(
        planner=PlannerAgent(engine, "p"),
        ideator=IdeatorAgent(engine, "p"),
        selector=SelectorAgent(engine, "p"),
        generator=GeneratorAgent(engine, "p"),
        code_reviewer=CodeReviewAgent(engine, "p"),
        critic=CriticAgent(engine, "p"),
        judge=JudgeAgent(engine, "p"),
        vision=None,
        sandbox=_PassSandbox(),  # type: ignore[arg-type]
        blind_solvers=_PassSolvers(),  # type: ignore[arg-type]
        runs_dir=tmp_path,
        max_workers=4,
        max_refine=max_refine,
        ideator_count=2,
    )


def test_pipeline_produces_passing_candidate(tmp_path) -> None:
    engine = _build_engine()
    report = _pipeline(engine, tmp_path).run("원문...", "스펙", "전략")

    assert report.run_id
    passed = [v for v in report.candidates if v.test_outcome and v.test_outcome.passes]
    assert len(passed) == 2
    for v in passed:
        assert v.status == "PASS"
    assert report.ranking[0]["candidate_id"] in {v.candidate.candidate_id for v in passed}


def test_pipeline_source_never_leaks_to_ideators(tmp_path) -> None:
    engine = _build_engine()
    report = _pipeline(engine, tmp_path).run("기밀 원문 본문 Q19", "스펙", "전략")
    for role, prompt in engine.calls:
        if role in {RolePolicy.IDEATOR, RolePolicy.SELECTOR, RolePolicy.GENERATOR}:
            assert "기밀 원문 본문" not in prompt


def test_pipeline_refines_revise_candidates(tmp_path) -> None:
    engine = _Engine({
        "planner": [_PLANNER],
        "ideator": [_IDEAS[0]],
        "selector": [{"adopted_ideas": ["idea-1"], "rationale": "부합"}],
        "generator": [_CANDIDATE, _CANDIDATE],
        "code_reviewer": [_REVIEW_REVISE, _REVIEW_OK],
        "critic": [_CRITIC, _CRITIC],
        "judge": [_JUDGE],
    })
    report = _pipeline(engine, tmp_path, max_refine=2).run("원문", "스펙", "전략")
    assert any(v.attempts >= 2 for v in report.candidates)
    assert all(v.status == "PASS" for v in report.candidates)


def test_pipeline_writes_report_and_uses_blind(tmp_path) -> None:
    engine = _build_engine()
    pipeline = _pipeline(engine, tmp_path)
    report = pipeline.run("원문", "스펙", "전략")
    out = tmp_path / "report.json"
    assert out.is_file()
    assert pipeline.blind_calls == 2  # 후보 2건
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/agents/test_pipeline.py -v`
Expected: FAIL — 모듈 없음.

**Step 3: 구현**

`src/math_variant/agents/blind.py` — 블라인드 풀이 LLM 어댑터:
```python
"""블라인드 풀이 LLM 어댑터 — BlindSolver 계약(문제 본문만 입력)을 구현한다 (T07)."""

from __future__ import annotations

from math_variant.agents._common import request_structured
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine
from math_variant.services.blind_solver import BlindSolution


class LLMBlindSolver:
    """BLIND_SOLVER 역할을 호출해 후보 문제를 독립 풀이한다."""

    def __init__(self, engine: StructuredOutputEngine, prompt_bundle: str, solver_id: str) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle
        self.solver_id = solver_id

    def solve(self, problem_text: str) -> BlindSolution:
        prompt = f"{self.prompt_bundle}\n\n[문제 본문]\n{problem_text}"
        data = request_structured(
            self.engine,
            request_id=f"blind-{self.solver_id}",
            role=RolePolicy.BLIND_SOLVER,
            prompt=prompt,
            schema="BlindSolution",
        )
        return BlindSolution.model_validate({**data, "solver_id": self.solver_id})
```

`src/math_variant/agents/pipeline.py`:
```python
"""다중 에이전트 병렬 파이프라인 오케스트레이터 (T07).

흐름:
  0. 기획(PLANNER) → 스펙·전략
  1. 발상(IDEATOR ×N 병렬, 고온) → 아이디어
  2. 선별(SELECTOR) → 채택 청사진
  3. 생성(GENERATOR ×N 병렬) → 후보 + 검증 스크립트 (+ 도형 필요 시 VISION)
  4. 검증(후보별 병렬): CODE_REVIEW → 샌드박스 실행 → BLIND A/B → CRITIC
  5. 집계(JUDGE) + 개선 루프(REVISE/저점수 재생성, 최대 max_refine 회)

원문 접근 경계: 원문 본문은 PLANNER 에만 전달된다.
후보의 PASS 는 "검증 스크립트가 샌드박스에서 PASS 판정"을 받을 때만 부여된다 (fail-closed).
"""

from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from math_variant.agents.code_reviewer import CodeReviewAgent
from math_variant.agents.critic import CriticAgent
from math_variant.agents.generator import GeneratorAgent
from math_variant.agents.ideator import IdeatorAgent, build_ideation_brief
from math_variant.agents.judge import JudgeAgent
from math_variant.agents.planner import PlannerAgent
from math_variant.agents.schemas import (
    CodeReviewOutput,
    CriticOutput,
    GeneratorOutput,
    IdeationOutput,
    PlannerOutput,
    ProductionStrategy,
)
from math_variant.agents.selector import SelectorAgent
from math_variant.agents.vision_artist import VisionArtist
from math_variant.domain.candidate import CandidateProblem
from math_variant.sandbox.provider import SandboxProvider
from math_variant.services.blind_solver import BlindConsensus
from math_variant.verifiers.test_runner import VerificationOutcome, build_verification_request, run_verification


class BlindPair(Protocol):
    """블라인드 합의 실행기 계약 (BlindSolver 를 충족한다)."""

    def solve_both(self, problem_text: str) -> BlindConsensus: ...


class CandidateVerdict(BaseModel):
    """후보 하나의 전체 검증 상태."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate: CandidateProblem
    blueprint_title: str
    code_review: CodeReviewOutput | None = None
    test_outcome: VerificationOutcome | None = None
    blind_consensus: BlindConsensus | None = None
    critic: CriticOutput | None = None
    attempts: int = 1
    status: Literal["PASS", "FAIL", "UNRESOLVED", "REVISE"] = "UNRESOLVED"


class PipelineReport(BaseModel):
    """파이프라인 실행 결과 컨테이너."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    planner: PlannerOutput
    ideas: list[IdeationOutput]
    adopted_ideas: list[str]
    candidates: list[CandidateVerdict]
    ranking: list[dict[str, Any]] = Field(default_factory=list)


def _to_strategy_dict(strategy: ProductionStrategy) -> dict[str, Any]:
    return {
        "difficulty_target": strategy.difficulty_target,
        "preservation_goals": strategy.preservation_goals,
        "variation_direction": strategy.variation_direction,
        "quality_criteria": strategy.quality_criteria,
        "constraints": strategy.constraints,
    }


class AgentPipeline:
    """역할 에이전트들을 병렬·순차로 오케스트레이션한다."""

    def __init__(
        self,
        planner: PlannerAgent,
        ideator: IdeatorAgent,
        selector: SelectorAgent,
        generator: GeneratorAgent,
        code_reviewer: CodeReviewAgent,
        critic: CriticAgent,
        judge: JudgeAgent,
        vision: VisionArtist | None,
        sandbox: SandboxProvider,
        blind_solvers: BlindPair,
        runs_dir: Path,
        ideator_count: int = 3,
        max_workers: int = 4,
        max_refine: int = 2,
    ) -> None:
        self.planner = planner
        self.ideator = ideator
        self.selector = selector
        self.generator = generator
        self.code_reviewer = code_reviewer
        self.critic = critic
        self.judge = judge
        self.vision = vision
        self.sandbox = sandbox
        self.blind_solvers = blind_solvers
        self.runs_dir = runs_dir
        self.ideator_count = ideator_count
        self.max_workers = max_workers
        self.max_refine = max_refine
        self.blind_calls = 0

    def run(self, source_text: str, strategy_brief: str = "") -> PipelineReport:
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        planner_out = self.planner.plan(source_text)
        strategy = _to_strategy_dict(planner_out.strategy)
        if not strategy_brief:
            strategy_brief = json.dumps(strategy, ensure_ascii=False)

        ideation_brief = build_ideation_brief(
            core_concepts=planner_out.core_concepts,
            objective=planner_out.objective,
            answer_type=planner_out.answer_type,
            domain=planner_out.domain,
            preservation_goals=planner_out.preservation_goals,
            strategy=strategy,
        )
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            ideas = list(
                pool.map(
                    lambda seed: self.ideator.ideate(ideation_brief, seed=str(seed)),
                    range(self.ideator_count),
                )
            )
        selection = self.selector.select(ideas, strategy_brief)
        adopted = [i for i in ideas if i.idea_id in set(selection.adopted_ideas)]

        candidates = self._generate_and_verify(run_id, adopted, ideation_brief, strategy_brief)
        rank_entries = [
            {
                "candidate_id": v.candidate.candidate_id,
                "problem_text": v.candidate.problem_text,
                "test_pass": bool(v.test_outcome and v.test_outcome.passes),
                "blind": v.blind_consensus.status.value if v.blind_consensus else "NONE",
                "critic_score": v.critic.score if v.critic else None,
                "attempts": v.attempts,
            }
            for v in candidates
        ]
        judge_out = self.judge.judge(rank_entries)
        ranking = judge_out.ranking if judge_out.ranking else rank_entries

        report = PipelineReport(
            run_id=run_id,
            planner=planner_out,
            ideas=ideas,
            adopted_ideas=selection.adopted_ideas,
            candidates=candidates,
            ranking=ranking,
        )
        self._write_report(run_id, report)
        return report

    def _generate_and_verify(
        self,
        run_id: str,
        blueprints: list[IdeationOutput],
        ideation_brief: str,
        strategy_brief: str,
    ) -> list[CandidateVerdict]:
        verdicts: list[CandidateVerdict] = []
        for index, blueprint in enumerate(blueprints):
            candidate_id = f"cand-{index + 1}"
            verdict = self._grow_candidate(
                run_id, candidate_id, blueprint, ideation_brief, strategy_brief
            )
            verdicts.append(verdict)
        return verdicts

    def _grow_candidate(
        self,
        run_id: str,
        candidate_id: str,
        blueprint: IdeationOutput,
        ideation_brief: str,
        strategy_brief: str,
        feedback: str = "",
        attempts: int = 1,
    ) -> CandidateVerdict:
        blueprint_dict = {
            "title": blueprint.title,
            "preserved_concepts": blueprint.preserved_concepts,
            "changed_dimensions": [d.value for d in blueprint.changed_dimensions],
            "construction_blueprint": blueprint.construction_blueprint,
        }
        candidate, extra = self.generator.generate(
            candidate_id=candidate_id,
            blueprint=blueprint_dict,
            brief=ideation_brief,
            feedback=feedback,
        )
        review = self.code_reviewer.review(
            extra.verification_script, candidate.problem_text, candidate.final_answer_claim
        )
        test_outcome: VerificationOutcome | None = None
        if review.approves:
            request = build_verification_request(
                f"{run_id}-{candidate_id}-v{attempts}",
                extra.verification_script,
                problem_context={
                    "problem_text": candidate.problem_text,
                    "claimed_answer": candidate.final_answer_claim,
                },
            )
            test_outcome = run_verification(self.sandbox, request)
        consensus = self.blind_solvers.solve_both(candidate.problem_text)
        self.blind_calls += 1
        critic = self.critic.criticize(candidate.problem_text, ideation_brief, strategy_brief)

        if self.vision is not None and (extra.needs_figure or blueprint.figure_required):
            self.vision.render(candidate_id, extra.figure_notes or blueprint.figure_notes,
                               candidate.problem_text)

        status: Literal["PASS", "FAIL", "UNRESOLVED", "REVISE"]
        if test_outcome is not None and test_outcome.passes:
            status = "PASS"
            candidate.mark_verified("PASS", f"{run_id}:sandbox-test")
        elif review.verdict == "REVISE" or (critic.recommendation == "REVISE" and attempts < self.max_refine):
            status = "REVISE"
        elif test_outcome is not None and test_outcome.verdict.value == "FAIL":
            status = "FAIL"
        else:
            status = "UNRESOLVED"

        if status == "REVISE" and attempts < self.max_refine:
            feedback = review.feedback or "; ".join(critic.comments)
            return self._grow_candidate(
                run_id, candidate_id, blueprint, ideation_brief, strategy_brief,
                feedback=feedback, attempts=attempts + 1,
            )

        verdict = CandidateVerdict(
            candidate=candidate,
            blueprint_title=blueprint.title,
            code_review=review,
            test_outcome=test_outcome,
            blind_consensus=consensus,
            critic=critic,
            attempts=attempts,
            status=status,
        )
        if test_outcome is not None and not test_outcome.passes:
            candidate.mark_verified("FAIL", run_id)
        return verdict

    def _write_report(self, run_id: str, report: PipelineReport) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        (self.runs_dir / "report.json").write_text(
            json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
```

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/agents/test_pipeline.py -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/math_variant/agents tests/unit/agents/test_pipeline.py
git commit -m "feat: add multi-agent pipeline orchestrator with refine loop"
```

---

## Task 8: CLI `run` 명령과 문제19 데모 배선

**Files:**
- Modify: `src/math_variant/cli.py`
- Create: `tests/unit/cli/test_run_command.py`

**Step 1: 실패 테스트 작성**

`tests/unit/cli/test_run_command.py`:
```python
"""T07 — CLI run 명령 테스트."""

from __future__ import annotations

from math_variant.cli import parse_run_args, resolve_source_question


def test_parse_run_args_defaults_to_gwangmyeongbukgo_q19() -> None:
    args = parse_run_args([])
    assert args.question_number == "19"
    assert "광명북고" in args.source_path


def test_parse_run_args_overrides() -> None:
    args = parse_run_args(["시험지/기타.json", "21"])
    assert args.question_number == "21"
    assert args.source_path == "시험지/기타.json"


def test_resolve_source_question_finds_19() -> None:
    from math_variant.cli import REPO_ROOT

    source = REPO_ROOT / "시험지" / "[2023년 기출] 광명북고1-2 중간 (주)_structured.json"
    question = resolve_source_question(source, "19")
    assert question is not None
    assert question["question_number"] == "19"
    assert "포물선" in question["question_text"]
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/cli/test_run_command.py -v`
Expected: FAIL — `parse_run_args` 없음.

**Step 3: 구현**

`cli.py`에 추가 (기존 import 블록 아래):
```python
_DEFAULT_SOURCE = "시험지/[2023년 기출] 광명북고1-2 중간 (주)_structured.json"


def parse_run_args(argv: list[str]) -> argparse.Namespace:
    """run 명령 인자 파서 (기본값: 광명북고 2023 Q19)."""
    parser = argparse.ArgumentParser(prog="math-variant run")
    parser.add_argument("source_path", nargs="?", default=_DEFAULT_SOURCE)
    parser.add_argument("question_number", nargs="?", default="19")
    return parser.parse_args(argv)


def resolve_source_question(source_path: Path, question_number: str) -> dict[str, Any] | None:
    """시험지 JSON 파일에서 문항 번호로 원문을 찾는다."""
    import json

    questions = json.loads(source_path.read_text(encoding="utf-8"))
    return next((q for q in questions if str(q["question_number"]) == question_number), None)


def run_pipeline(argv: list[str] | None = None) -> int:
    """LLM 다중 에이전트 파이프라인을 실행하고 결과를 출력한다."""
    args = parse_run_args(argv or [])
    source_path = Path(args.source_path)
    if not source_path.is_absolute():
        source_path = REPO_ROOT / source_path
    if not source_path.is_file():
        print(f"시험지 파일 없음: {source_path}", file=sys.stderr)
        return 1
    question = resolve_source_question(source_path, args.question_number)
    if question is None:
        print(f"문항 없음: {args.question_number}", file=sys.stderr)
        return 1

    from math_variant.agents.blind import LLMBlindSolver
    from math_variant.agents.code_reviewer import CodeReviewAgent
    from math_variant.agents.critic import CriticAgent
    from math_variant.agents.generator import GeneratorAgent
    from math_variant.agents.ideator import IdeatorAgent
    from math_variant.agents.judge import JudgeAgent
    from math_variant.agents.pipeline import AgentPipeline
    from math_variant.agents.planner import PlannerAgent
    from math_variant.agents.schemas import register_agent_schemas
    from math_variant.agents.selector import SelectorAgent
    from math_variant.agents.vision_artist import VisionArtist
    from math_variant.providers.factory import build_provider_registry
    from math_variant.providers.registry import SchemaRegistry
    from math_variant.providers.resolver import RoleResolver
    from math_variant.providers.settings import ProviderSettings
    from math_variant.providers.structured import StructuredOutputEngine
    from math_variant.sandbox.provider import DockerSandboxProvider
    from math_variant.security.prompt_firewall import ForbiddenContentScanner
    from math_variant.services.blind_solver import BlindSolver

    settings = ProviderSettings()
    registry = build_provider_registry(settings)
    schemas = SchemaRegistry()
    register_agent_schemas(schemas)
    resolver = RoleResolver(settings.role_policy(), registry)
    engine = StructuredOutputEngine(primary=None, fallback=None, schemas=schemas)
    engine.role_resolver = resolver

    prompts = PROMPTS_DIR

    def _prompt(name: str) -> str:
        return (prompts / name).read_text(encoding="utf-8")

    scanner = ForbiddenContentScanner({"원문 정답": "8sqrt(2)"})

    figures_dir = Path("runs") / "figures"
    pipeline = AgentPipeline(
        planner=PlannerAgent(engine, _prompt("planner.md")),
        ideator=IdeatorAgent(engine, _prompt("ideator.md")),
        selector=SelectorAgent(engine, _prompt("selector.md")),
        generator=GeneratorAgent(engine, _prompt("candidate_generator.md")),
        code_reviewer=CodeReviewAgent(engine, _prompt("code_reviewer.md")),
        critic=CriticAgent(engine, _prompt("critic.md")),
        judge=JudgeAgent(engine, _prompt("judge.md")),
        vision=VisionArtist(engine, _prompt("vision.md"), figures_dir),
        sandbox=DockerSandboxProvider(image="math-variant-sandbox:test"),  # type: ignore[arg-type]
        blind_solvers=BlindSolver(
            LLMBlindSolver(engine, _prompt("blind_solver.md"), "A"),
            LLMBlindSolver(engine, _prompt("blind_solver.md"), "B"),
            {"원문 정답": question.get("answer", ""), "해설": ""},
        ),
        runs_dir=Path("runs"),
        ideator_count=3,
        max_refine=2,
    )

    from math_variant.services.normalize import normalize_source

    report = pipeline.run(normalize_source(question["question_text"]), "")

    print("=" * 70)
    print(f"run_id: {report.run_id}")
    print(f"원문 문항 {args.question_number}: {question['question_text'][:80]}...")
    print("-" * 70)
    for i, entry in enumerate(report.ranking, start=1):
        candidate = next(
            (v for v in report.candidates if v.candidate.candidate_id == entry["candidate_id"]), None
        )
        if candidate is None:
            continue
        print(f"[{i}] {candidate.candidate.candidate_id} (score {entry.get('score', '-')})")
        print(f"    상태: {candidate.status.value}")
        print(f"    문제: {candidate.candidate.problem_text}")
        print(f"    주장 답: {candidate.candidate.final_answer_claim}")
        if candidate.test_outcome:
            print(f"    샌드박스 검증: {candidate.test_outcome.verdict.value} "
                  f"({candidate.test_outcome.detail[:80]})")
        if candidate.blind_consensus:
            print(f"    블라인드 합의: {candidate.blind_consensus.status.value}")
        if candidate.critic:
            print(f"    비평 점수: {candidate.critic.score:.1f}")
        print()
    return 0
```

`main()`에 분기 추가:
```python
    if command == "run":
        return run_pipeline(args[1:])
```

`cli.py` 최상단에 `import argparse`, `from typing import Any` 및 `PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"` 추가.

**Step 4: 테스트 실행 (통과 확인)**

Run: `.venv\Scripts\python -m pytest tests/unit/cli/test_run_command.py -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/math_variant/cli.py tests/unit/cli/test_run_command.py
git commit -m "feat: add cli run command for multi-agent pipeline (Q19 demo)"
```

---

## Task 9: 통합 검증 — 실제 Docker 샌드박스에서 sympy 스크립트 실행

**Files:**
- Create: `tests/integration/agents/test_sandbox_verification.py`

**Step 1: 실패 테스트 작성**

`tests/integration/agents/test_sandbox_verification.py`:
```python
"""T07 — 실제 Docker 샌드박스에서 검증 스크립트 실행 통합 테스트."""

from __future__ import annotations

import pytest

from math_variant.sandbox.provider import DockerSandboxProvider
from math_variant.verifiers.test_runner import (
    TestVerdict,
    build_verification_request,
    run_verification,
)

pytestmark = pytest.mark.docker

_IMAGE = "math-variant-sandbox:test"


@pytest.fixture(scope="module")
def sandbox() -> DockerSandboxProvider:
    return DockerSandboxProvider(image=_IMAGE)


def test_sympy_script_passing_verdict(sandbox: DockerSandboxProvider) -> None:
    script = (
        "from sympy import symbols, solve, sqrt\n"
        "x, a = symbols('x a')\n"
        "claimed = 8*sqrt(2)\n"
        "assert claimed == 8*sqrt(2)\n"
        "result = {'verdict': 'PASS', 'detail': 'claimed value matches'}\n"
    )
    request = build_verification_request("it-pass", script, {"problem_text": "문제"})
    outcome = run_verification(sandbox, request)
    assert outcome.verdict == TestVerdict.PASS
    assert outcome.image_digest is not None


def test_failing_script_is_fail(sandbox: DockerSandboxProvider) -> None:
    script = (
        "from sympy import symbols\n"
        "x = symbols('x')\n"
        "assert x**2 + 1 != 0, '실패해야 한다'\n"
        "result = {'verdict': 'PASS'}\n"
    )
    request = build_verification_request("it-fail", script, {})
    outcome = run_verification(sandbox, request)
    assert outcome.verdict == TestVerdict.FAIL


def test_malicious_script_is_unresolved(sandbox: DockerSandboxProvider) -> None:
    script = (
        "import os\n"
        "result = {'verdict': 'PASS'}\n"
    )
    request = build_verification_request("it-mal", script, {})
    outcome = run_verification(sandbox, request)
    assert outcome.verdict == TestVerdict.UNRESOLVED
```

> 참고: 이 테스트는 `docker` 마커라 데몬 없으면 자동 skip된다 (conftest 정책). 로컬에서 실행하려면 `math-variant-sandbox:test` 이미지가 필요하다.

**Step 2: 테스트 실행**

Run: `.venv\Scripts\python -m pytest tests/integration/agents/test_sandbox_verification.py -v`
Expected: docker 데몬·이미지 없으면 skip. 있으면 PASS/FAIL/UNRESOLVED 판정 확인.

**Step 3: 커밋**

```bash
git add tests/integration/agents/test_sandbox_verification.py
git commit -m "test: add docker integration tests for verification script runner"
```

---

## Task 10: 전체 품질 게이트 + 회귀 확인

**Step 1: 전체 테스트 실행**

Run: `.venv\Scripts\python -m pytest -q`
Expected: 전체 PASS (기존 102+ + 신규). docker/live 마커는 환경에 따라 skip.

**Step 2: lint·format·typecheck**

Run: `.venv\Scripts\python -m ruff check src tests infra`
Run: `.venv\Scripts\python -m ruff format --check src tests infra`
Run: `.venv\Scripts\python -m mypy`
Expected: 모두 통과. mypy strict 경고가 있으면 해당 파일을 고친다 (`disallow_any_generics`, `strict`).

**Step 3: tasks 인덱스 갱신**

Modify: `tasks/TASKS_INDEX.md` — T07 항목 2~3개 추가 (에이전트 파이프라인, 검증 스크립트 러너, CLI run).

**Step 4: 커밋**

```bash
git add tasks/TASKS_INDEX.md
git commit -m "docs: register T07 multi-agent pipeline tasks"
```

---

## 검증 요약 (완료 기준)

1. `pytest` 전체 통과 (신규: 6개 테스트 파일, ~30 케이스).
2. ruff/mypy strict 통과.
3. `math-variant run` 실행 시 광명북고 Q19 원문 → 기획 → 발상(병렬 3) → 선별 → 생성 → 코드리뷰 → 샌드박스 검증 → 블라인드 → 비평 → 집계 → `runs/report.json` + `runs/figures/*.tex` 산출.
4. IDEATOR/SELECTOR/GENERATOR 프롬프트에 원문 본문이 절대 포함되지 않음(단위 테스트로 고정).
5. PASS는 샌드박스 검증 스크립트 PASS 시에만 부여, REVISE는 피드백 재생성(최대 2회).

# 웹 레퍼런스 레이어 노출 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** M1~M6 레퍼런스 계층(참조 검색·스킬 매핑·스타일 정렬)을 웹의 진행상황·결과 페이지에서 확인·활용 가능하게 한다. 웹 파이프라인 기본 엔진을 LangChain으로 전환하되 `MATH_VARIANT_PIPELINE_ENGINE` 환경변수로 기존 httpx 엔진 복귀 가능.

**Architecture:** `EventStage`에 `REFERENCE`/`SKILL_MAPPING`/`STYLE_ALIGN`을 추가하고 양 파이프라인(httpx `AgentPipeline`, LangGraph `LangChainPipeline`)이 이벤트를 발행한다. `PipelineReport.reference_summary`(additive 기본 None)와 `CandidateVerdict.style_aligned`(기본 False)로 결과 데이터를 추가하고, `adapters.py`가 RunStore로 전달한다. 프론트는 `ProgressView`(신규 단계 3개)와 검토 화면(`CandidateCard` 스킬 배지·정렬 배지, `ReviewClient` 참조 요약 패널)을 확장한다.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, LangChain/LangGraph, pytest. Next.js 16.3(App Router, `params`는 Promise — 이미 반영됨), React 19, Vitest. 게이트: ruff/mypy/pytest(백엔드), eslint/tsc/vitest(프론트).

**주의 (web/AGENTS.md):** 이 Next.js는 16.3으로 breaking changes가 있다. 컴포넌트만 수정하므로 라우팅 API는 건드리지 않는다. 작성 전 `web/node_modules/next/dist/docs/`의 관련 가이드를 참고할 것.

---

### Task 1: EventStage 확장 + 이벤트 `data` 파라미터

**Files:**
- Modify: `src/math_variant/events.py:17-29`
- Modify: `src/math_variant/agents/pipeline.py:154-174` (`_emit`)
- Modify: `src/math_variant/langchain_generator/pipeline.py:107-133` (`EventEmitter.emit`)
- Test: `tests/unit/events/test_events.py`

**Step 1: Write the failing test**

`tests/unit/events/test_events.py`에 추가:

```python
def test_event_stage_includes_reference_layer_stages() -> None:
    """참조 검색·스킬 매핑·스타일 정렬 단계 값이 존재한다 (웹 진행 화면용)."""
    assert EventStage.REFERENCE.value == "reference"
    assert EventStage.SKILL_MAPPING.value == "skill_mapping"
    assert EventStage.STYLE_ALIGN.value == "style_align"


def test_pipeline_event_carries_data_payload() -> None:
    """단계 이벤트가 요약 데이터를 실어 나를 수 있다."""
    event = PipelineEvent(
        event_id="stage-1",
        type="stage",
        stage=EventStage.REFERENCE,
        status="done",
        message="참조 자산 주입 완료",
        data={"exam_patterns": 3, "condition_phrasings": 5, "style_unit": "도형의 방정식"},
    )
    assert event.data["exam_patterns"] == 3
    assert event.data["style_unit"] == "도형의 방정식"
```

(파일의 기존 import에 `EventStage`, `PipelineEvent`가 없으면 추가.)

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\events\test_events.py -q`
Expected: FAIL — `AttributeError: REFERENCE`

**Step 3: Write minimal implementation**

`src/math_variant/events.py`:

```python
class EventStage(StrEnum):
    """파이프라인 진행 단계."""

    PLANNER = "planner"
    REFERENCE = "reference"
    IDEATION = "ideation"
    SELECTION = "selection"
    GENERATION = "generation"
    CODE_REVIEW = "code_review"
    SANDBOX = "sandbox"
    BLIND = "blind"
    CRITIC = "critic"
    SKILL_MAPPING = "skill_mapping"
    STYLE_ALIGN = "style_align"
    JUDGE = "judge"
    DONE = "done"
```

`src/math_variant/agents/pipeline.py` `_emit` 시그니처와 PipelineEvent 생성부:

```python
def _emit(
    self,
    stage: EventStage,
    status: Literal["started", "done", "failed"],
    message: str = "",
    candidate_id: str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    if self.on_event is None:
        return
    self._event_seq += 1
    seq = self._event_seq
    self.on_event(
        PipelineEvent(
            event_id=f"stage-{seq}",
            type="stage",
            stage=stage,
            status=status,
            message=message,
            candidate_id=candidate_id,
            data=data or {},
        )
    )
```

`src/math_variant/langchain_generator/pipeline.py` `EventEmitter.emit` 동일하게 `data` 파라미터 추가:

```python
def emit(
    self,
    stage: EventStage,
    status: Literal["started", "done", "failed"],
    message: str = "",
    candidate_id: str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    if self.on_event is None:
        return
    self.seq += 1
    self.on_event(
        PipelineEvent(
            event_id=f"stage-{self.seq}",
            type="stage",
            stage=stage,
            status=status,
            message=message,
            candidate_id=candidate_id,
            data=data or {},
        )
    )
```

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\events\test_events.py tests\unit\agents\test_pipeline_events.py -q`
Expected: PASS

**Step 5: Commit**

```powershell
git -C .. add generateQuestion6/src/math_variant/events.py generateQuestion6/src/math_variant/agents/pipeline.py generateQuestion6/src/math_variant/langchain_generator/pipeline.py generateQuestion6/tests/unit/events/test_events.py
git -C .. commit -m "feat(events): add reference/skill_mapping/style_align stages and event data payload"
```

---

### Task 2: 참조 요약 빌더 (`reference/sections.py`)

**Files:**
- Modify: `src/math_variant/reference/sections.py`
- Test: `tests/unit/reference/test_sections.py`

**Step 1: Write the failing test**

`tests/unit/reference/test_sections.py`에 추가 (파일 상단 import 확인):

```python
from math_variant.reference.models import ConditionPhrasing, ExamPatternCard, SolutionStyle
from math_variant.reference.sections import build_reference_summary


def test_build_reference_summary_compresses_results() -> None:
    """검색 결과를 리포트용 요약으로 압축한다."""
    summary = build_reference_summary(
        [
            ExamPatternCard(
                topic_id="t1",
                unit="도형의 방정식",
                pattern="접선의 방정식",
                wording="접선을 구하시오",
                example_abstract="원에 접선",
                source_count=2,
            )
        ],
        [
            ConditionPhrasing(
                topic_id="t1",
                unit="도형의 방정식",
                patterns=["조건 A"],
                wording_conventions=["관례 B"],
            )
        ],
        SolutionStyle(unit="도형의 방정식", open="주어진", close="구하는 값은",
                      justification_vocab=["따라서"]),
    )
    assert summary is not None
    assert summary["exam_patterns"][0]["unit"] == "도형의 방정식"
    assert summary["exam_patterns"][0]["source_count"] == 2
    assert summary["condition_phrasings"]["count"] == 2
    assert summary["condition_phrasings"]["topics"] == ["도형의 방정식"]
    assert summary["style_guide"]["justification_vocab"] == ["따라서"]


def test_build_reference_summary_returns_none_when_empty() -> None:
    """검색 결과가 전부 비어 있으면 None (기존 run 데이터와 호환)."""
    assert build_reference_summary([], [], None) is None
```

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\reference\test_sections.py::test_build_reference_summary_compresses_results -q`
Expected: FAIL — ImportError

**Step 3: Write minimal implementation**

`src/math_variant/reference/sections.py` 하단에 추가 (`collections.abc`의 `Sequence` import, 모델 import 확인):

```python
def build_reference_summary(
    patterns: Sequence[ExamPatternCard] | None,
    phrasings: Sequence[ConditionPhrasing] | None,
    style: SolutionStyle | None,
) -> dict[str, Any] | None:
    """참조 자산 검색 결과를 실행 리포트용 요약으로 압축한다.

    모두 비어 있으면 None 을 반환한다 (레퍼런스 비활성 실행과 호환).
    """
    if not patterns and not phrasings and style is None:
        return None
    return {
        "exam_patterns": [
            {
                "topic_id": p.topic_id,
                "unit": p.unit,
                "pattern": p.pattern,
                "source_count": p.source_count,
            }
            for p in (patterns or [])
        ],
        "condition_phrasings": {
            "count": sum(
                len(c.patterns) + len(c.wording_conventions) for c in (phrasings or [])
            ),
            "topics": [c.unit for c in (phrasings or [])],
        },
        "style_guide": (
            {
                "unit": style.unit,
                "justification_vocab": style.justification_vocab,
            }
            if style is not None
            else None
        ),
    }
```

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\reference\test_sections.py -q`
Expected: PASS

**Step 5: Commit**

```powershell
git -C .. add generateQuestion6/src/math_variant/reference/sections.py generateQuestion6/tests/unit/reference/test_sections.py
git -C .. commit -m "feat(reference): add build_reference_summary for run report"
```

---

### Task 3: httpx 파이프라인 — REFERENCE·SKILL_MAPPING 이벤트 + report 요약

**Files:**
- Modify: `src/math_variant/agents/pipeline.py:69-95` (`CandidateVerdict`, `PipelineReport`)
- Modify: `src/math_variant/agents/pipeline.py:201-216` (`run()` 참조 검색 블록)
- Modify: `src/math_variant/agents/pipeline.py:307-314` (report 생성)
- Modify: `src/math_variant/agents/pipeline.py:399-403` (`_grow_candidate` 스킬 매핑)
- Test: `tests/unit/agents/test_pipeline_events.py`

**Step 1: Write the failing test**

`tests/unit/agents/test_pipeline_events.py`에 추가:

```python
from math_variant.reference.models import ConditionPhrasing, ExamPatternCard, SolutionStyle


class _FakeReferenceRunnable:
    def invoke(self, payload: dict) -> dict:
        return {
            "patterns": [
                ExamPatternCard(
                    topic_id="t1",
                    unit="도형의 방정식",
                    pattern="접선의 방정식",
                    wording="접선을 구하시오",
                    example_abstract="원에 접선",
                    source_count=2,
                )
            ],
            "phrasings": [
                ConditionPhrasing(
                    topic_id="t1",
                    unit="도형의 방정식",
                    patterns=["조건 A"],
                    wording_conventions=["관례 B"],
                )
            ],
            "style": SolutionStyle(
                unit="도형의 방정식", open="주어진", close="구하는 값은",
                justification_vocab=["따라서"],
            ),
        }


def test_pipeline_emits_reference_and_skill_mapping_events(tmp_path) -> None:
    engine = _Engine(
        {
            "planner": [_PLANNER],
            "ideator": [_IDEA],
            "selector": [{"adopted_ideas": ["idea-1"], "rationale": "부합"}],
            "generator": [_CANDIDATE],
            "code_reviewer": [_REVIEW],
            "critic": [_CRITIC],
            "judge": [_JUDGE],
        }
    )
    events: list[PipelineEvent] = []
    pipeline = _build_pipeline(engine, tmp_path, events.append)
    pipeline.reference_runnable = _FakeReferenceRunnable()  # type: ignore[assignment]
    report = pipeline.run("원문")

    ref_events = [e for e in events if e.stage == EventStage.REFERENCE]
    assert [e.status for e in ref_events] == ["started", "done"]
    assert ref_events[-1].data["exam_patterns"] == 1
    assert ref_events[-1].data["condition_phrasings"] == 1
    assert ref_events[-1].data["style_unit"] == "도형의 방정식"

    skill_events = [e for e in events if e.stage == EventStage.SKILL_MAPPING]
    assert skill_events
    assert skill_events[0].candidate_id == "cand-1"
    assert skill_events[-1].data["total"] == 1

    assert report.reference_summary is not None
    assert report.reference_summary["exam_patterns"][0]["pattern"] == "접선의 방정식"
    assert report.candidates[0].style_aligned is False
```

또한 기존 `test_pipeline_emits_stage_events_in_order`의 `expected` 목록에 `SKILL_MAPPING` 추가 (아래 Step 3에서 정확한 순서 확인):

```python
    expected = [
        EventStage.PLANNER,
        EventStage.IDEATION,
        EventStage.SELECTION,
        EventStage.GENERATION,
        EventStage.SKILL_MAPPING,
        EventStage.CODE_REVIEW,
        EventStage.SANDBOX,
        EventStage.BLIND,
        EventStage.CRITIC,
        EventStage.JUDGE,
    ]
```

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\agents\test_pipeline_events.py -q`
Expected: FAIL — REFERENCE·SKILL_MAPPING 미발행 + 순서 불일치

**Step 3: Write minimal implementation**

`src/math_variant/agents/pipeline.py`:

1. `CandidateVerdict`에 `style_aligned: bool = False` 추가 (status 앞):

```python
    attempts: int = 1
    style_aligned: bool = False
    status: Literal["PASS", "FAIL", "UNRESOLVED", "REVISE"] = "UNRESOLVED"
```

2. `PipelineReport`에 필드 추가:

```python
    ranking: list[dict[str, Any]] = Field(default_factory=list)
    reference_summary: dict[str, Any] | None = None
```

3. import 추가 (파일 상단, 기존 reference import 구간에 맞춰):

```python
from math_variant.reference.models import ConditionPhrasing, ExamPatternCard, SolutionStyle
from math_variant.reference.sections import (
    build_reference_summary,
    generator_condition_section,
    generator_style_section,
    ideator_pattern_section,
)
```

(기존 import 구문의 형태를 유지 — 파일 현재 상태 확인 후 `sections` import에 `build_reference_summary`만 추가하면 됨.)

4. `run()`의 참조 검색 블록 교체 (기존 lines 201-216):

```python
        p_sec = ""
        c_sec = ""
        s_sec = ""
        ref_patterns: list[ExamPatternCard] = []
        ref_phrasings: list[ConditionPhrasing] = []
        ref_style: SolutionStyle | None = None
        if self.reference_runnable is not None:
            topics = ",".join(planner_out.core_concepts)
            if topics:
                self._emit(
                    EventStage.REFERENCE,
                    "started",
                    "참조 자산(출제 패턴·조건 관례·해설 가이드) 검색",
                )
                ref_res = self.reference_runnable.invoke({"topics": topics})
                ref_patterns = ref_res.get("patterns", [])
                ref_phrasings = ref_res.get("phrasings", [])
                ref_style = ref_res.get("style")
                p_sec = ideator_pattern_section(ref_patterns)
                c_sec = generator_condition_section(ref_phrasings)
                s_sec = generator_style_section(ref_style)
                self._emit(
                    EventStage.REFERENCE,
                    "done",
                    "참조 자산 주입 완료",
                    data={
                        "exam_patterns": len(ref_patterns),
                        "condition_phrasings": len(ref_phrasings),
                        "style_unit": ref_style.unit if ref_style else None,
                    },
                )
```

5. report 생성부 (line 307)에 `reference_summary` 추가:

```python
        report = PipelineReport(
            run_id=run_id,
            planner=planner_out,
            ideas=ideas,
            adopted_ideas=selection.adopted_ideas,
            candidates=candidates,
            ranking=ranking,
            reference_summary=build_reference_summary(ref_patterns, ref_phrasings, ref_style),
        )
```

6. `_grow_candidate` 스킬 매핑 블록 교체 (lines 399-403):

```python
        self._emit(EventStage.SKILL_MAPPING, "started", "지식체계 스킬 매핑", candidate_id)
        skill_evidences = assign_skill_ids(
            candidate.solution_steps,
            concepts=core_concepts or blueprint.preserved_concepts,
        )
        candidate.transformation_evidence.extend(skill_evidences)
        matched = sum(1 for ev in skill_evidences if ev.get("skill_id") is not None)
        self._emit(
            EventStage.SKILL_MAPPING,
            "done",
            f"매핑 완료 ({matched}/{len(skill_evidences)})",
            candidate_id,
            data={"matched": matched, "total": len(skill_evidences)},
        )
```

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\agents\test_pipeline_events.py tests\unit\agents\test_pipeline.py tests\unit\reference\test_skill_mapping_pipeline.py -q`
Expected: PASS (기존 순서 테스트는 Step 1에서 수정한 expected로 통과)

**Step 5: Commit**

```powershell
git -C .. add generateQuestion6/src/math_variant/agents/pipeline.py generateQuestion6/tests/unit/agents/test_pipeline_events.py
git -C .. commit -m "feat(pipeline): emit reference/skill_mapping events and attach reference_summary"
```

---

### Task 4: LangChain 파이프라인 — REFERENCE·SKILL_MAPPING·STYLE_ALIGN 이벤트 + state

**Files:**
- Modify: `src/math_variant/langchain_generator/pipeline.py:164-203` (`PipelineState`에 `style_aligned` 추가)
- Modify: `src/math_variant/langchain_generator/pipeline.py:235-268` (`_enrich_references_node`)
- Modify: `src/math_variant/langchain_generator/pipeline.py:393-397` (스킬 매핑 블록)
- Modify: `src/math_variant/langchain_generator/pipeline.py:575-607` (`_style_align_node`)
- Modify: `src/math_variant/langchain_generator/pipeline.py:647-664` (`_verdict`)
- Modify: `src/math_variant/langchain_generator/pipeline.py:708-725` (`_report_node`)
- Test: `tests/unit/langchain_generator/test_style_align.py`, `tests/unit/langchain_generator/test_enrich_references.py`

**Step 1: Write the failing test**

`tests/unit/langchain_generator/test_style_align.py`의 기존 `test_style_align_node_pure_function` 수정 — `DummyRuntime`에 emit 컨텍스트를 주고 STYLE_ALIGN 이벤트·`style_aligned` 반환을 검증:

```python
def test_style_align_node_pure_function() -> None:
    from math_variant.domain.candidate import CandidateProblem, Formalization

    cand = CandidateProblem(
        candidate_id="cand-1",
        plan_id="plan-1",
        problem_text="원의 중심을 구하시오.",
        formalization=Formalization(symbols=["x"], constraints=[], goal="중심"),
        final_answer_claim="(0,0)",
        solution_steps=[
            SolutionStepClaim(step_id="1", statement="원 방정식 정리", justification="공식"),
            SolutionStepClaim(step_id="2", statement="중심 산출", justification="답"),
        ],
    )
    style_guide = SolutionStyle(
        unit="원의 방정식",
        open="주어진 원의",
        transform_order=["표준형 변환"],
        justification_vocab=["따라서", "그러므로"],
        close="구하는 값은",
        sample_step="표준형으로 정리한다.",
    )

    class DummyEmit:
        def __init__(self) -> None:
            self.events: list[tuple] = []

        def emit(self, stage, status, message="", candidate_id=None, data=None) -> None:
            self.events.append((stage, status, data))

    class DummyContext:
        emit = DummyEmit()

    class DummyRuntime:
        context = DummyContext()

    state = {"candidate": cand, "style_guide": style_guide, "candidate_id": "cand-1"}
    res = _style_align_node(state, DummyRuntime())  # type: ignore[arg-type]
    aligned_cand = res.get("candidate")
    assert aligned_cand is not None
    assert "따라서" in aligned_cand.solution_steps[1].justification
    assert res.get("style_aligned") is True
    from math_variant.events import EventStage

    stages = [e[0] for e in DummyContext.emit.events]  # type: ignore[union-attr]
    assert EventStage.STYLE_ALIGN in stages
```

그리고 `test_langchain_pipeline_with_style_align_enabled` 확장 — `build_pipeline_graph`에 `on_event`와 `reference_runnable`(스타일 가이드 반환 fake) 전달:

```python
class _StyleRunnable:
    def invoke(self, payload: dict) -> dict:
        from math_variant.reference.models import SolutionStyle

        return {
            "patterns": [],
            "phrasings": [],
            "style": SolutionStyle(
                unit="도형의 방정식", open="주어진", close="구하는 값은",
                justification_vocab=["따라서"],
            ),
        }


def test_langchain_pipeline_emits_style_align_and_summary(tmp_path: Path) -> None:
    """그래프 실행 시 STYLE_ALIGN·REFERENCE 이벤트와 reference_summary·style_aligned 반영."""
    # 주의: 바로 위 test_langchain_pipeline_with_style_align_enabled 의
    # shared_data dict·engine = MockTrackingEngine(shared_data)·_p 헬퍼를 그대로
    # 복사해 사용한다 (에이전트·프롬프트 구성 동일). `...` 자리에 각 에이전트 인자를 채운다.
    events: list[Any] = []
    pipeline = build_pipeline_graph(
        planner=PlannerAgent(engine, _p("planner.md")),
        ideator=IdeatorAgent(engine, _p("ideator.md")),
        selector=SelectorAgent(engine, _p("selector.md")),
        generator=GeneratorAgent(engine, _p("candidate_generator.md")),
        code_reviewer=CodeReviewAgent(engine, _p("code_reviewer.md")),
        critic=CriticAgent(engine, _p("critic.md")),
        judge=JudgeAgent(engine, _p("judge.md")),
        vision=None,
        sandbox=MockSandboxProvider(),
        blind_solvers=MockBlindSolver(),
        runs_dir=tmp_path / "runs",
        ideator_count=1,
        on_event=events.append,
        reference_runnable=_StyleRunnable(),
        enable_style_align=True,
    )

    from math_variant.events import EventStage

    report = pipeline.run("원문 텍스트")
    stages = [e.stage for e in events]
    assert EventStage.REFERENCE in stages
    assert EventStage.STYLE_ALIGN in stages
    assert report.candidates[0].style_aligned is True
    assert report.reference_summary is not None
    assert report.reference_summary["style_guide"]["unit"] == "도형의 방정식"
```

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\langchain_generator\test_style_align.py -q`
Expected: FAIL — `DummyRuntime.context`가 None이라 `_style_align_node`가 `AttributeError` / 새 테스트는 `style_aligned`·summary 없음

**Step 3: Write minimal implementation**

1. `PipelineState`에 추가 (line 192 `candidate: CandidateProblem` 근처):

```python
    candidate: CandidateProblem
    style_aligned: bool
```

2. `_enrich_references_node` — REFERENCE 단계로 변경 + data:

```python
    if ctx.reference_runnable is not None and topics:
        ctx.emit.emit(
            EventStage.REFERENCE, "started", "참조 자산(출제 패턴·조건 관례·해설 가이드) 검색"
        )
        ref_res = ctx.reference_runnable.invoke({"topics": topics})
        pats = ref_res.get("patterns", [])
        conds = ref_res.get("phrasings", [])
        style = ref_res.get("style")
        p_sec = ideator_pattern_section(pats)
        c_sec = generator_condition_section(conds)
        s_sec = generator_style_section(style)
        ctx.emit.emit(
            EventStage.REFERENCE,
            "done",
            "참조 자산 주입 완료",
            data={
                "exam_patterns": len(pats),
                "condition_phrasings": len(conds),
                "style_unit": style.unit if style else None,
            },
        )
```

3. 스킬 매핑 블록 (lines 393-397) 이벤트 추가:

```python
    ctx.emit.emit(
        EventStage.SKILL_MAPPING, "started", "지식체계 스킬 매핑", state["candidate_id"]
    )
    skill_evidences = assign_skill_ids(
        candidate.solution_steps,
        concepts=core_concepts,
    )
    candidate.transformation_evidence.extend(skill_evidences)
    matched = sum(1 for ev in skill_evidences if ev.get("skill_id") is not None)
    ctx.emit.emit(
        EventStage.SKILL_MAPPING,
        "done",
        f"매핑 완료 ({matched}/{len(skill_evidences)})",
        state["candidate_id"],
        data={"matched": matched, "total": len(skill_evidences)},
    )
```

4. `_style_align_node` — 이벤트 + `style_aligned` 반환:

```python
def _style_align_node(
    state: PipelineState, runtime: Runtime[PipelineContext]
) -> dict[str, Any]:
    """해설 스타일 가이드(solveSkill grounding 패턴)에 따라 풀이 단계를 정렬한다 (M6)."""
    ctx = runtime.context
    style_guide = state.get("style_guide")
    candidate = state.get("candidate")
    ctx.emit.emit(
        EventStage.STYLE_ALIGN, "started", "해설 스타일 가이드 정렬", state.get("candidate_id")
    )
    if style_guide is None or candidate is None or not candidate.solution_steps:
        ctx.emit.emit(
            EventStage.STYLE_ALIGN,
            "done",
            "정렬 대상 없음 — 생략",
            state.get("candidate_id"),
            data={"applied": False},
        )
        return {}

    aligned_steps: list[SolutionStepClaim] = []
    vocab = style_guide.justification_vocab or ["따라서"]
    primary_vocab = vocab[0] if vocab else "따라서"
    applied = False

    for i, step in enumerate(candidate.solution_steps):
        statement = step.statement
        justification = step.justification

        # 마지막 단계에 결론 어구 정렬
        if i == len(candidate.solution_steps) - 1:
            if not any(v in justification or v in statement for v in vocab):
                justification = f"{primary_vocab} {justification}".strip()
                applied = True

        aligned_steps.append(
            SolutionStepClaim(
                step_id=step.step_id,
                statement=statement,
                justification=justification,
                claimed=step.claimed,
            )
        )

    candidate.solution_steps = aligned_steps
    ctx.emit.emit(
        EventStage.STYLE_ALIGN,
        "done",
        "스타일 정렬 완료",
        state.get("candidate_id"),
        data={"applied": applied, "vocab": vocab},
    )
    return {"candidate": candidate, "style_aligned": applied}
```

5. `_verdict` — CandidateVerdict에 `style_aligned` 전달:

```python
    return CandidateVerdict(
        candidate=candidate,
        blueprint_title=state["blueprint"].title,
        code_review=review,
        test_outcome=test_outcome,
        blind_consensus=state.get("consensus"),
        critic=critic,
        attempts=state["attempts"],
        style_aligned=state.get("style_aligned", False),
        status=status,
    )
```

6. `_report_node` — summary 추가:

```python
    report = PipelineReport(
        run_id=state["run_id"],
        planner=state["planner_out"],
        ideas=state.get("ideas", []),
        adopted_ideas=state["selection_out"].adopted_ideas,
        candidates=verdicts,
        ranking=state.get("ranking", []),
        reference_summary=build_reference_summary(
            state.get("exam_patterns"),
            state.get("condition_refs"),
            state.get("style_guide"),
        ),
    )
```

(`build_reference_summary` import 추가 — 파일 상단 `reference.sections` import 구간에.)

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\langchain_generator -q`
Expected: PASS

**Step 5: Commit**

```powershell
git -C .. add generateQuestion6/src/math_variant/langchain_generator/pipeline.py generateQuestion6/tests/unit/langchain_generator/test_style_align.py
git -C .. commit -m "feat(langchain): emit reference/skill/style events and carry style_aligned + summary"
```

---

### Task 5: 어댑터·스토리지 — `reference_summary`·`style_aligned` 노출

**Files:**
- Modify: `src/math_variant/api/adapters.py:20-27, 68-99`
- Modify: `src/math_variant/api/storage.py:93-100` (`public_run`)
- Test: `tests/unit/api/test_adapters.py`

**Step 1: Write the failing test**

`tests/unit/api/test_adapters.py`의 `test_report_to_run_store_maps_candidates`에 추가하고 새 테스트 작성:

```python
def test_report_to_run_store_carries_reference_summary_and_style_flag() -> None:
    verdict = _pass_verdict()
    report = PipelineReport(
        run_id="run-1",
        planner=_planner(),
        ideas=[],
        adopted_ideas=[],
        candidates=[verdict],
        ranking=[],
        reference_summary={
            "exam_patterns": [{"topic_id": "t1", "unit": "도형의 방정식",
                               "pattern": "접선", "source_count": 2}],
            "condition_phrasings": {"count": 2, "topics": ["도형의 방정식"]},
            "style_guide": {"unit": "도형의 방정식", "justification_vocab": ["따라서"]},
        },
    )
    data = report_to_run_store(report)
    assert data["reference_summary"]["exam_patterns"][0]["unit"] == "도형의 방정식"
    assert data["candidates"][0]["style_aligned"] is False
    json.dumps(data, ensure_ascii=False)


def test_report_to_run_store_defaults_reference_summary_to_none() -> None:
    report = PipelineReport(
        run_id="run-1", planner=_planner(), ideas=[], adopted_ideas=[],
        candidates=[_pass_verdict()], ranking=[],
    )
    data = report_to_run_store(report)
    assert data["reference_summary"] is None
```

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\api\test_adapters.py -q`
Expected: FAIL — KeyError

**Step 3: Write minimal implementation**

`src/math_variant/api/adapters.py`:

1. `report_to_run_store` 반환 dict에 추가:

```python
        "candidates": [_candidate_to_dict(v) for v in report.candidates],
        "reference_summary": report.reference_summary,
        "created_at": report.created_at.isoformat(),
```

2. `_candidate_to_dict` 반환 dict에 추가 (`"verification_status": status,` 다음 줄 근처):

```python
        "style_aligned": verdict.style_aligned,
```

`src/math_variant/api/storage.py` `public_run` 반환 dict에 추가:

```python
        return {
            "run_id": data.get("run_id", run_id),
            "state": data.get("state", "UNKNOWN"),
            "source": data.get("source"),
            "candidates": visible,
            "reference_summary": data.get("reference_summary"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }
```

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\api -q`
Expected: PASS

**Step 5: Commit**

```powershell
git -C .. add generateQuestion6/src/math_variant/api/adapters.py generateQuestion6/src/math_variant/api/storage.py generateQuestion6/tests/unit/api/test_adapters.py
git -C .. commit -m "feat(api): expose reference_summary and style_aligned in run store"
```

---

### Task 6: 팩토리·웹 API — 엔진 전환 + `enable_style_align`

**Files:**
- Modify: `src/math_variant/pipeline_factory.py:170-227` (`build_pipeline`)
- Modify: `src/math_variant/api/app.py:120-187` (`PipelineRunner._execute`) + 모듈 함수 추가
- Test: `tests/unit/api/test_generation_api.py`

**Step 1: Write the failing test**

`tests/unit/api/test_generation_api.py`에 추가:

```python
from math_variant.api.app import resolve_engine, resolve_style_align


def test_resolve_engine_defaults_to_langchain() -> None:
    """웹 기본 엔진은 langchain. env 로 기존 엔진 복귀 가능."""
    assert resolve_engine(None) == "langchain"
    assert resolve_engine("") == "langchain"
    assert resolve_engine("bogus") == "langchain"
    assert resolve_engine("default") == "default"
    assert resolve_engine("langchain") == "langchain"


def test_resolve_style_align_defaults_on() -> None:
    """웹 기본 스타일 정렬은 켬. env=0 으로 끌 수 있다."""
    assert resolve_style_align(None) is True
    assert resolve_style_align("1") is True
    assert resolve_style_align("0") is False
    assert resolve_style_align("false") is False
```

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\api\test_generation_api.py -q`
Expected: FAIL — ImportError

**Step 3: Write minimal implementation**

`src/math_variant/pipeline_factory.py` `build_pipeline` 시그니처에 추가하고 LangChain 분기에 전달:

```python
def build_pipeline(
    *,
    engine: Literal["default", "langchain"] | None = None,
    ...
    reference_runnable: Runnable[dict[str, str], dict[str, Any]] | None = None,
    enable_style_align: bool | None = None,
) -> PipelineRunnerProtocol:
```

LangChain 분기:

```python
        return build_langchain_pipeline(
            ...
            reference_runnable=runnable,
            enable_style_align=enable_style_align,
        )
```

`src/math_variant/api/app.py` — 상단 `import os` 추가 후 모듈 함수:

```python
def resolve_engine(env_value: str | None) -> Literal["default", "langchain"]:
    """웹 기본 엔진은 langchain. MATH_VARIANT_PIPELINE_ENGINE=default 로 복귀 가능."""
    return env_value if env_value in {"default", "langchain"} else "langchain"


def resolve_style_align(env_value: str | None) -> bool:
    """웹 기본 스타일 정렬은 켬. MATH_VARIANT_STYLE_ALIGN=0 으로 끌 수 있다."""
    return (env_value or "1").strip() == "1"
```

`PipelineRunner._execute`의 `build_pipeline` 호출부 수정:

```python
            pipeline = build_pipeline(
                engine=resolve_engine(os.getenv("MATH_VARIANT_PIPELINE_ENGINE")),
                ideator_count=int(options.get("ideator_count", 3)),
                max_refine=int(options.get("max_refine", 2)),
                on_event=_on_event,
                runs_dir=Path("runs") / "artifacts" / job_id,
                figures_dir=Path("runs") / "artifacts" / job_id / "figures",
                sandbox_image=self.sandbox_image,
                enable_style_align=resolve_style_align(os.getenv("MATH_VARIANT_STYLE_ALIGN")),
            )
```

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\api\test_generation_api.py tests\unit\test_pipeline_factory.py -q`
Expected: PASS

**Step 5: Commit**

```powershell
git -C .. add generateQuestion6/src/math_variant/pipeline_factory.py generateQuestion6/src/math_variant/api/app.py generateQuestion6/tests/unit/api/test_generation_api.py
git -C .. commit -m "feat(api): default web engine to langchain with env-var fallback"
```

---

### Task 7: 프론트 타입 확장

**Files:**
- Modify: `web/src/lib/types.ts:49-65, 83-90`

**Step 1: 타입 수정**

`web/src/lib/types.ts`:

```ts
export interface TransformationEvidence {
  dimension: string;
  step_id?: string;
  skill_id?: string | null;
  concept_name?: string;
  reason?: string;
  description?: string;
}

export interface ReferenceSummary {
  exam_patterns: {
    topic_id: string;
    unit: string;
    pattern: string;
    source_count: number;
  }[];
  condition_phrasings: { count: number; topics: string[] };
  style_guide: { unit: string; justification_vocab: string[] } | null;
}
```

`Candidate` 인터페이스:

```ts
  transformation_evidence: TransformationEvidence[];
  style_aligned?: boolean;
```

`GenerationRun` 인터페이스:

```ts
  candidates: Candidate[];
  reference_summary?: ReferenceSummary | null;
```

**Step 2: 타입체크**

Run (web 디렉터리): `npm run typecheck`
Expected: 통과 (아직 소비처가 없으므로 통과해야 함)

**Step 3: Commit**

```powershell
git -C .. add generateQuestion6/web/src/lib/types.ts
git -C .. commit -m "feat(web): extend types for reference summary and skill mapping"
```

---

### Task 8: ProgressView — 신규 단계 3개

**Files:**
- Modify: `web/src/components/ProgressView.tsx:10-34`
- Test: `web/src/components/__tests__/ProgressView.test.tsx`

**Step 1: Write the failing test**

`ProgressView.test.tsx`에 추가:

```tsx
it("레퍼런스 레이어 단계가 체크리스트에 표시된다", async () => {
  vi.spyOn(api, "getJob").mockResolvedValue(makeJob());
  vi.spyOn(api, "streamJobEvents").mockImplementation(() => () => {});

  render(<ProgressView jobId="run-1" />);

  expect(await screen.findByTestId("stage-reference")).toHaveTextContent("참조 검색");
  expect(screen.getByTestId("stage-skill_mapping")).toHaveTextContent("스킬 매핑");
  expect(screen.getByTestId("stage-style_align")).toHaveTextContent("스타일 정렬");
});
```

**Step 2: Run test to verify it fails**

Run (web 디렉터리): `npm run test -- ProgressView`
Expected: FAIL — stage-reference 없음

**Step 3: Write minimal implementation**

`ProgressView.tsx`:

```ts
const STAGE_ORDER = [
  "planner",
  "reference",
  "ideation",
  "selection",
  "generation",
  "code_review",
  "sandbox",
  "blind",
  "critic",
  "skill_mapping",
  "style_align",
  "judge",
  "done",
];

const STAGE_LABELS: Record<string, string> = {
  planner: "기획",
  reference: "참조 검색",
  ideation: "발상",
  selection: "선별",
  generation: "생성",
  code_review: "코드 심사",
  sandbox: "샌드박스 검증",
  blind: "블라인드 합의",
  critic: "비평",
  skill_mapping: "스킬 매핑",
  style_align: "스타일 정렬",
  judge: "집계",
  done: "완료",
};
```

**Step 4: Run test to verify it passes**

Run (web 디렉터리): `npm run test -- ProgressView`
Expected: PASS

**Step 5: Commit**

```powershell
git -C .. add generateQuestion6/web/src/components/ProgressView.tsx generateQuestion6/web/src/components/__tests__/ProgressView.test.tsx
git -C .. commit -m "feat(web): show reference/skill/style stages in progress checklist"
```

---

### Task 9: CandidateCard — 스킬 매핑 표시 + 스타일 정렬 배지

**Files:**
- Modify: `web/src/components/CandidateCard.tsx`
- Test: `web/src/components/__tests__/CandidateCard.test.tsx`

**Step 1: Write the failing test**

`CandidateCard.test.tsx`에 추가 (`CandidateList` 렌더 경유):

```tsx
import { CandidateList } from "../CandidateList";

it("skill_mapping 증거와 스타일 정렬 배지를 표시한다", () => {
  const candidate = makeCandidate({
    transformation_evidence: [
      { dimension: "representation" },
      {
        dimension: "skill_mapping",
        step_id: "s1",
        skill_id: "101",
        concept_name: "원의 방정식",
      },
    ],
    style_aligned: true,
  });
  render(<CandidateList candidates={[candidate]} onDecide={vi.fn()} />);

  expect(screen.getByText("스타일 정렬됨")).toBeInTheDocument();
  // 주의: 해설 배지와 변형 설명 항목 양쪽에 나타나므로 getAllByText 사용
  expect(screen.getAllByText(/skill 101 · 원의 방정식/).length).toBeGreaterThan(0);
});

it("매핑 실패한 단계는 '매핑 없음'으로 표시한다", () => {
  const candidate = makeCandidate({
    transformation_evidence: [
      { dimension: "skill_mapping", step_id: "s1", skill_id: null, reason: "no_match" },
    ],
  });
  render(<CandidateList candidates={[candidate]} onDecide={vi.fn()} />);

  expect(screen.getByText(/매핑 없음/)).toBeInTheDocument();
  expect(screen.queryByText("스타일 정렬됨")).not.toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run (web 디렉터리): `npm run test -- CandidateCard`
Expected: FAIL — 텍스트 없음

**Step 3: Write minimal implementation**

`CandidateCard.tsx`:

```tsx
import { EvidencePanel } from "./EvidencePanel";
import { ReviewActions } from "./ReviewActions";
import { RubricView } from "./RubricView";
import { LatexText } from "@/lib/latex";
import type { Candidate, Decision, TransformationEvidence } from "@/lib/types";

function skillForStep(
  evidence: TransformationEvidence[],
  stepId: string,
): { skill_id: string; concept_name?: string } | null {
  const entry = evidence.find(
    (e) => e.dimension === "skill_mapping" && e.step_id === stepId,
  );
  if (!entry || entry.skill_id == null) {
    return null;
  }
  return { skill_id: entry.skill_id, concept_name: entry.concept_name };
}
```

헤더에 배지 (candidate-title span 뒤):

```tsx
        {candidate.style_aligned ? (
          <span className="style-align-badge">스타일 정렬됨</span>
        ) : null}
```

해설 단계 — map 콜백을 블록 바디로 바꿔 스킬 변수를 지역 선언 (non-null assertion 금지):

```tsx
        <ol className="candidate-solution">
          {candidate.solution_steps.map((step, index) => {
            const skill = skillForStep(candidate.transformation_evidence, step.step_id);
            return (
              <li key={step.step_id}>
                <span className="solution-index">{index + 1}</span>
                <span className="solution-statement">
                  <LatexText text={step.statement} />
                </span>
                {skill ? (
                  <span className="skill-badge">
                    skill {skill.skill_id} · {skill.concept_name ?? "개념"}
                  </span>
                ) : null}
              </li>
            );
          })}
        </ol>
```

변형 설명 목록 교체:

```tsx
        <ul className="candidate-transformation">
          {candidate.transformation_evidence.map((entry, index) =>
            entry.dimension === "skill_mapping" ? (
              <li key={`${candidate.candidate_id}-t${index}`}>
                <span className="transform-dot" />
                단계 {entry.step_id} →{" "}
                {entry.skill_id
                  ? `skill ${entry.skill_id} · ${entry.concept_name ?? "개념"}`
                  : "매핑 없음"}
              </li>
            ) : (
              <li key={`${candidate.candidate_id}-t${index}`}>
                <span className="transform-dot" />
                {entry.dimension}
              </li>
            ),
          )}
        </ul>
```

**Step 4: Run test to verify it passes**

Run (web 디렉터리): `npm run test -- CandidateCard`
Expected: PASS

**Step 5: Commit**

```powershell
git -C .. add generateQuestion6/web/src/components/CandidateCard.tsx generateQuestion6/web/src/components/__tests__/CandidateCard.test.tsx
git -C .. commit -m "feat(web): render skill mapping badges and style align badge on candidate card"
```

---

### Task 10: ReviewClient — 참조 요약 패널 + 스타일(CSS)

**Files:**
- Modify: `web/src/app/runs/[runId]/review/ReviewClient.tsx:46-73`
- Modify: `web/src/app/globals.css` (배지·패널 스타일)
- Create: `web/src/app/runs/[runId]/review/__tests__/ReviewClient.test.tsx`

**Step 1: Write the failing test**

새 파일 `ReviewClient.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReviewClient } from "../ReviewClient";
import * as api from "@/lib/api";

function makeRun(overrides: Record<string, unknown> = {}) {
  return {
    run_id: "run-1",
    state: "GENERATED",
    source: { mode: "text", text: "원문" },
    candidates: [],
    created_at: "",
    updated_at: "",
    ...overrides,
  } as never;
}

describe("ReviewClient 참조 요약 패널", () => {
  it("reference_summary 가 있으면 참조 요약 패널을 표시한다", async () => {
    vi.spyOn(api, "getRun").mockResolvedValue(
      makeRun({
        reference_summary: {
          exam_patterns: [
            { topic_id: "t1", unit: "도형의 방정식", pattern: "접선의 방정식", source_count: 2 },
          ],
          condition_phrasings: { count: 2, topics: ["도형의 방정식"] },
          style_guide: { unit: "도형의 방정식", justification_vocab: ["따라서"] },
        },
      }),
    );

    render(<ReviewClient runIdPromise={Promise.resolve({ runId: "run-1" })} />);

    const panel = await screen.findByTestId("reference-summary");
    expect(panel).toHaveTextContent("접선의 방정식");
    expect(panel).toHaveTextContent("2건");
    expect(panel).toHaveTextContent("따라서");
  });

  it("reference_summary 가 없으면 패널을 표시하지 않는다", async () => {
    vi.spyOn(api, "getRun").mockResolvedValue(makeRun());

    render(<ReviewClient runIdPromise={Promise.resolve({ runId: "run-1" })} />);

    expect(await screen.findByText(/후보 비교/)).toBeInTheDocument();
    expect(screen.queryByTestId("reference-summary")).not.toBeInTheDocument();
  });
});
```

**Step 2: Run test to verify it fails**

Run (web 디렉터리): `npm run test -- ReviewClient`
Expected: FAIL — reference-summary 없음

**Step 3: Write minimal implementation**

`ReviewClient.tsx` — `원본 문항` 섹션 앞(또는 뒤)에 패널 삽입:

```tsx
      {run.reference_summary ? (
        <section
          className="reference-summary"
          data-testid="reference-summary"
          aria-label="참조 요약"
        >
          <h2>참조 요약</h2>
          <div className="reference-summary-grid">
            <div>
              <h3>기출 패턴 ({run.reference_summary.exam_patterns.length})</h3>
              <ul>
                {run.reference_summary.exam_patterns.map((pattern) => (
                  <li key={pattern.topic_id}>
                    {pattern.unit} · {pattern.pattern} ({pattern.source_count}건)
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3>조건 표현 관례</h3>
              <p>
                {run.reference_summary.condition_phrasings.count}건 ·{" "}
                {run.reference_summary.condition_phrasings.topics.join(", ") || "없음"}
              </p>
            </div>
            <div>
              <h3>해설 스타일 가이드</h3>
              {run.reference_summary.style_guide ? (
                <p>
                  {run.reference_summary.style_guide.unit} · 결론 어휘:{" "}
                  {run.reference_summary.style_guide.justification_vocab.join(", ")}
                </p>
              ) : (
                <p>없음</p>
              )}
            </div>
          </div>
        </section>
      ) : null}
```

`globals.css` — 기존 카드 스타일(예: `.review-source`, `.candidate-card` 구간)의 색상·간격 관례를 따르는 스타일 추가:

```css
.style-align-badge {
  display: inline-block;
  margin-left: 0.5rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: #dcfce7;
  color: #166534;
  font-size: 0.75rem;
  vertical-align: middle;
}

.skill-badge {
  display: inline-block;
  margin-left: 0.5rem;
  padding: 0.1rem 0.4rem;
  border-radius: 6px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.75rem;
}

.reference-summary {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 1rem 1.25rem;
  margin: 1rem 0;
}

.reference-summary h2 {
  margin: 0 0 0.75rem;
  font-size: 1.05rem;
}

.reference-summary h3 {
  margin: 0 0 0.35rem;
  font-size: 0.9rem;
  color: #475569;
}

.reference-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.reference-summary ul {
  margin: 0;
  padding-left: 1.1rem;
}
```

(기존 globals.css의 디자인 토큰과 어긋나면 파일을 읽고 변수 사용으로 조정.)

**Step 4: Run test to verify it passes**

Run (web 디렉터리): `npm run test -- ReviewClient`
Expected: PASS

**Step 5: Commit**

```powershell
git -C .. add generateQuestion6/web/src/app/runs/[runId]/review/ReviewClient.tsx generateQuestion6/web/src/app/runs/[runId]/review/__tests__/ReviewClient.test.tsx generateQuestion6/web/src/app/globals.css
git -C .. commit -m "feat(web): add reference summary panel to review screen"
```

---

### Task 11: 전체 게이트 + 회귀 확인

**Step 1: 백엔드 게이트 (전부 통과해야 함)**

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests scratch\build_exam_patterns.py scratch\build_condition_style_index.py scratch\build_solution_style_guide.py scratch\build_scope_profile.py
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest tests\unit -q
.\.venv\Scripts\python.exe scratch\verify_parity.py
```

Expected:
- ruff: `All checks passed!`
- mypy: `Success: no issues found`
- pytest: 전체 통과 (기존 243개 + 신규)
- verify_parity: 8개 `[PASS]`

**Step 2: 프론트 게이트 (web 디렉터리)**

```powershell
npm run lint
npm run typecheck
npm run test
```

Expected: 전부 통과

**Step 3: 수동 확인 (선택)**

1. 백엔드 실행: `.\.venv\Scripts\python.exe -m uvicorn math_variant.api.app:app --port 8000`
2. 웹 실행: `npm run dev` (web 디렉터리)
3. `/create`에서 문제 생성 → 진행상황에 참조 검색/스킬 매핑/스타일 정렬 단계 표시 확인 → 검토 화면에서 참조 요약 패널·스킬 배지·정렬 배지 확인.
4. `MATH_VARIANT_PIPELINE_ENGINE=default`로 재시작 → 기존 엔진 동작 확인 (스타일 정렬 단계는 안 나타남).

**Step 4: 최종 커밋 (남은 변경이 있으면)**

```powershell
git -C .. status
git -C .. add generateQuestion6/...
git -C .. commit -m "chore: final gate fixes for web reference exposure"
```

---

## 검증 요약 (완료 기준)

- [ ] `EventStage`에 `reference`·`skill_mapping`·`style_align` 존재, 양 엔진이 이벤트 발행.
- [ ] 웹 API 기본 엔진 langchain, `MATH_VARIANT_PIPELINE_ENGINE=default` 복귀 가능, 스타일 정렬 env(`MATH_VARIANT_STYLE_ALIGN`, 기본 1) 반영.
- [ ] run 데이터에 `reference_summary`, 후보에 `style_aligned` 노출 (`/api/runs/{id}`).
- [ ] 진행상황 페이지에 신규 3단계 표시.
- [ ] 결과 페이지: 스킬 매핑(단계 배지·변형 설명), 스타일 정렬 배지, 참조 요약 패널.
- [ ] ruff/mypy/pytest + eslint/tsc/vitest 전부 통과, `verify_parity` 8개 PASS.
- [ ] 기존 243개 단위 테스트 + 신규 테스트 전부 green.

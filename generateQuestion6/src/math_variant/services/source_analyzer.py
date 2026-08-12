"""Source Analyzer — 정규화 원문에서 ProblemSpec 을 추출한다 (T02.4).

두 경로:
1. `DeterministicSourceAnalyzer` — 지원 도메인(도형의 방정식) 규칙 기반 추출 (오프라인 골드).
2. `SourceAnalyzer` — 구조화 출력 엔진(LLM)을 이용한 일반 텍스트 추출.
   LLM 이 확정하지 못한 가정은 `unresolved_assumptions` 로 반환되어 자동 경로를 막는다.

`golden_compare` — 골드 fixture 의 핵심 필드와 추출 결과를 비교한다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from math_variant.domain.problem import MathStatement, ProblemSpec
from math_variant.domain.scope import ScopeProfile
from math_variant.errors import ErrorCode, MathVariantError, StructuredError
from math_variant.providers.contracts import RolePolicy, StructuredRequest
from math_variant.providers.structured import StructuredOutputEngine


class StatementOutput(BaseModel):
    """LLM 응답의 진술 항목."""

    model_config = ConfigDict(extra="forbid")

    id: str
    natural_language: str
    sympy_expr: str | None = None
    domain: str | None = None


class ProblemSpecOutput(BaseModel):
    """Source Analyzer LLM 응답 스키마."""

    model_config = ConfigDict(extra="forbid")

    core_concepts: list[str] = Field(min_length=1)
    auxiliary_concepts: list[str] = Field(default_factory=list)
    givens: list[StatementOutput] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    objective: StatementOutput
    answer_type: str
    explicit_assumptions: list[str] = Field(default_factory=list)
    implicit_domain: list[str] = Field(default_factory=list)
    expected_methods: list[str] = Field(default_factory=list)
    unresolved_assumptions: list[str] = Field(default_factory=list)

    def to_spec(self, spec_id: str, source_text: str, scope: ScopeProfile) -> ProblemSpec:
        return ProblemSpec(
            spec_id=spec_id,
            source_text=source_text,
            curriculum_version=scope.curriculum_version,
            exam_scope=list(scope.exam_scope),
            core_concepts=self.core_concepts,
            auxiliary_concepts=self.auxiliary_concepts,
            givens=[
                MathStatement(
                    id=s.id,
                    natural_language=s.natural_language,
                    sympy_expr=s.sympy_expr,
                    domain=s.domain,
                )
                for s in self.givens
            ],
            unknowns=self.unknowns,
            objective=MathStatement(
                id=self.objective.id,
                natural_language=self.objective.natural_language,
                sympy_expr=self.objective.sympy_expr,
                domain=self.objective.domain,
            ),
            answer_type=self.answer_type,  # type: ignore[arg-type]
            explicit_assumptions=self.explicit_assumptions,
            implicit_domain=self.implicit_domain,
            expected_methods=self.expected_methods,
            forbidden_knowledge=list(scope.forbidden_concepts),
            unresolved_assumptions=self.unresolved_assumptions,
        )


class SourceAnalyzer:
    """LLM 기반 구조 추출기."""

    def __init__(
        self, engine: StructuredOutputEngine, scope: ScopeProfile, prompt_bundle: str
    ) -> None:
        self.engine = engine
        self.scope = scope
        self.prompt_bundle = prompt_bundle

    def analyze(self, normalized_text: str) -> ProblemSpec:
        prompt = f"{self.prompt_bundle}\n\n[입력 문항]\n{normalized_text}"
        response = self.engine.generate_structured(
            StructuredRequest(
                request_id="source-analyze",
                role=RolePolicy.SOURCE_ANALYZER,
                prompt=prompt,
                response_schema="ProblemSpecOutput",
            ),
            policy=None,
        )
        if not response.ok or response.data is None:
            raise MathVariantError(
                StructuredError(
                    code=ErrorCode.SOURCE_UNRESOLVED,
                    message="Source Analyzer 가 구조화된 응답을 생성하지 못했다",
                    context={
                        "provider_error": response.error.model_dump() if response.error else None
                    },
                )
            )
        output = ProblemSpecOutput.model_validate(response.data)
        unknown_concepts = [
            c for c in output.core_concepts if c not in self.scope.concept_vocabulary
        ]
        if unknown_concepts:
            raise MathVariantError(
                StructuredError(
                    code=ErrorCode.SCOPE_VIOLATION,
                    message=f"범위 밖 핵심 개념: {unknown_concepts}",
                    context={"concepts": unknown_concepts},
                )
            )
        return output.to_spec(spec_id="auto", source_text=normalized_text, scope=self.scope)


_GOLDEN_KEY_FIELDS = (
    "core_concepts",
    "unknowns",
    "answer_type",
    "implicit_domain",
    "unresolved_assumptions",
)


class GoldenCompare:
    """골드 핵심 필드와 추출 결과를 비교한다 (결정론적)."""

    def __init__(self) -> None:
        self._failures: list[str] = []

    def __call__(self, spec: ProblemSpec, expected: dict[str, Any]) -> bool:
        self._failures = []

        if sorted(spec.core_concepts) != sorted(expected.get("core_concepts", [])):
            self._failures.append(
                f"core_concepts: {spec.core_concepts} != {expected.get('core_concepts', [])}"
            )
        if sorted(spec.unknowns) != sorted(expected.get("unknowns", [])):
            self._failures.append(f"unknowns: {spec.unknowns} != {expected.get('unknowns', [])}")
        if spec.answer_type != expected.get("answer_type"):
            self._failures.append(
                f"answer_type: {spec.answer_type} != {expected.get('answer_type')}"
            )
        if sorted(spec.implicit_domain) != sorted(expected.get("implicit_domain", [])):
            self._failures.append(
                f"implicit_domain: {spec.implicit_domain} != {expected.get('implicit_domain', [])}"
            )
        if sorted(spec.unresolved_assumptions) != sorted(
            expected.get("unresolved_assumptions", [])
        ):
            self._failures.append(
                f"unresolved_assumptions: {spec.unresolved_assumptions} != "
                f"{expected.get('unresolved_assumptions', [])}"
            )

        expected_givens = expected.get("givens", [])
        actual_givens = [{"id": g.id, "natural_language": g.natural_language} for g in spec.givens]
        if actual_givens != expected_givens:
            self._failures.append(f"givens: {actual_givens} != {expected_givens}")

        expected_objective = expected.get("objective", {})
        actual_objective = {"natural_language": spec.objective.natural_language}
        if actual_objective != expected_objective:
            self._failures.append(f"objective: {actual_objective} != {expected_objective}")

        return not self._failures

    def report(self, spec: ProblemSpec, expected: dict[str, Any]) -> str:
        self(spec, expected)
        return "; ".join(self._failures) or "골드 일치"


golden_compare = GoldenCompare()

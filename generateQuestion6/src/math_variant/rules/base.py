"""변형 규칙 카탈로그 모델 (T04.1).

각 규칙은 rule_id, 전제(preconditions), 변경 차원(changed_dimensions),
구성 청사진(construction_template), 난이도 변화(difficulty_delta),
검증 레시피(verifier_recipe), 상충 규칙(conflicts)을 명시한다.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from math_variant.domain.problem import ProblemSpec
from math_variant.domain.transformation import Dimension
from math_variant.errors import ErrorCode, MathVariantError, StructuredError


class RuleDefinition(BaseModel):
    """변형 규칙 하나."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str
    name: str
    description: str
    concepts: list[str] = Field(min_length=1)
    preconditions: list[str] = Field(min_length=1)
    changed_dimensions: list[Dimension] = Field(min_length=1)
    construction_template: str = Field(min_length=1)
    difficulty_delta: float = 0.0
    verifier_recipe: list[str] = Field(min_length=1)
    conflicts: list[str] = Field(default_factory=list)

    def applies_to(self, spec: ProblemSpec) -> bool:
        """전제 개념이 ProblemSpec 의 핵심·보조 개념에 모두 존재하는지 검사한다."""
        available = set(spec.core_concepts) | set(spec.auxiliary_concepts)
        return all(precondition in available for precondition in self.preconditions)


class RuleCatalog:
    """규칙 집합과 조합 검증."""

    def __init__(self, rules: list[RuleDefinition]) -> None:
        self._rules: dict[str, RuleDefinition] = {rule.rule_id: rule for rule in rules}

    def get(self, rule_id: str) -> RuleDefinition:
        return self._rules[rule_id]

    def all_rules(self) -> list[RuleDefinition]:
        return list(self._rules.values())

    def rules_for(self, spec: ProblemSpec) -> list[RuleDefinition]:
        return [rule for rule in self._rules.values() if rule.applies_to(spec)]

    def validate_combination(self, rule_ids: list[str]) -> None:
        """선택된 규칙들의 상충 관계를 결정론적으로 검사한다."""
        for rule_id in rule_ids:
            rule = self._rules[rule_id]
            for other_id in rule_ids:
                if other_id in rule.conflicts:
                    raise MathVariantError(
                        StructuredError(
                            code=ErrorCode.RULE_CONFLICT,
                            message=f"상충하는 규칙 조합: {rule_id} ↔ {other_id}",
                            context={"rule_a": rule_id, "rule_b": other_id},
                        )
                    )

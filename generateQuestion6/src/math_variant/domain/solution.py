"""SolutionGraph — 의존성 있는 풀이 단계와 채점 루브릭."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from math_variant.domain.problem import MathStatement

VerifierKind = Literal["sympy", "z3", "numeric", "human", "blind_solver"]


class SolutionNode(BaseModel):
    """풀이 그래프의 노드 하나."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    statement: MathStatement
    prerequisites: list[str] = Field(default_factory=list)
    justification: str = Field(default="")
    verifier: VerifierKind = "human"
    points: float = Field(ge=0)
    alternative_group: str | None = None
    fatal_if_wrong: bool = False
    # 원문 독립 풀이/생성기 풀이에서 아직 고정 검증되지 않은 주장을 표시한다.
    claimed: bool = True


class SolutionGraph(BaseModel):
    """검증된 풀이 경로의 DAG."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    graph_id: str
    nodes: list[SolutionNode] = Field(min_length=1)
    final_node_ids: list[str] = Field(min_length=1)
    total_points: float = Field(ge=0)

    @field_validator("total_points")
    @classmethod
    def _match_point_sum(cls, value: float, info: ValidationInfo) -> float:
        nodes = info.data.get("nodes")
        if nodes is not None:
            expected = round(sum(n.points for n in nodes), 6)
            if abs(value - expected) > 1e-9:
                raise ValueError(f"total_points({value}) != 노드 점수 합({expected})")
        return value

    @field_validator("final_node_ids")
    @classmethod
    def _final_nodes_exist(cls, value: list[str], info: ValidationInfo) -> list[str]:
        nodes = info.data.get("nodes")
        if nodes is not None:
            node_ids = {n.id for n in nodes}
            unknown = [fid for fid in value if fid not in node_ids]
            if unknown:
                raise ValueError(f"존재하지 않는 final node id: {unknown}")
        return value


class RubricItem(BaseModel):
    """부분점수 기준 하나 — 검증된 SolutionNode 에서만 파생된다."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str
    score: float = Field(ge=0)
    description: str
    equivalent_expressions: list[str] = Field(default_factory=list)
    common_errors: list[str] = Field(default_factory=list)
    alternative_paths: list[str] = Field(default_factory=list)


class Rubric(BaseModel):
    """SolutionGraph 에 연결된 채점 기준."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    graph_id: str
    items: list[RubricItem] = Field(default_factory=list)
    total_points: float = Field(ge=0)
    derived_from_verified: bool = False

    @field_validator("derived_from_verified")
    @classmethod
    def _must_be_verified_source(cls, value: bool, info: ValidationInfo) -> bool:
        if not value:
            raise ValueError("루브릭은 검증된 SolutionGraph 에서만 파생될 수 있다")
        return value

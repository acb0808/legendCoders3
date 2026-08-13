"""LangChain 기반 문제 생성 모듈 (병행 실행).

기존 httpx 기반 provider·에이전트 파이프라인과 독립적으로 동작하며,
기존 프롬프트(`prompts/*.md`)와 Pydantic 응답 스키마(`agents/schemas.py`)를
재사용한다. 기존 파이프라인 코드는 수정하지 않는다.

두 가지 실행 경로를 제공한다:
- 단일 패스 생성기 (`generator.py`) — planner→ideator→generator 후보 1건
- LangGraph 전체 파이프라인 (`pipeline.py`) — 기존 AgentPipeline 과 동일한
  전 단계(발상 병렬·선별·검증·블라인드·비평·심판·재생성 루프)의 드롭인 대체
"""

from __future__ import annotations

from math_variant.langchain_generator.chains import (
    JSON_SYSTEM_MESSAGE,
    build_structured_chain,
)
from math_variant.langchain_generator.engine import LangChainRoleEngine
from math_variant.langchain_generator.generator import (
    GeneratedCandidate,
    LangChainProblemGenerator,
    build_langchain_generator,
)
from math_variant.langchain_generator.pipeline import (
    LangChainPipeline,
    build_langchain_pipeline,
    build_pipeline_graph,
)

__all__ = [
    "JSON_SYSTEM_MESSAGE",
    "GeneratedCandidate",
    "LangChainPipeline",
    "LangChainProblemGenerator",
    "LangChainRoleEngine",
    "build_langchain_generator",
    "build_langchain_pipeline",
    "build_pipeline_graph",
    "build_structured_chain",
]

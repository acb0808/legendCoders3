"""에이전트 공통 헬퍼 — 구조화 요청 실행과 실패 처리."""

from __future__ import annotations

from typing import Any

from math_variant.errors import ErrorCode, MathVariantError, StructuredError
from math_variant.providers.contracts import RolePolicy, StructuredRequest
from math_variant.providers.structured import StructuredOutputEngine


def request_structured(
    engine: StructuredOutputEngine,
    request_id: str,
    role: RolePolicy,
    prompt: str,
    schema: str,
) -> dict[str, Any]:
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

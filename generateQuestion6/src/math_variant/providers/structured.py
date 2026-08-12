"""구조화 출력 엔진 — 파싱·검증·복구·폴백 상태 머신 (T02.3).

정책 (문서 02 §4.1):
- 공급자 응답을 서버에서 Pydantic 으로 재검증한다.
- 형식 복구 1회, 다른 공급자 폴백 1회를 상태 머신에 연결한다.
- 잘못된 출력이 다음 단계로 전달되는 경로는 0건이어야 한다.
"""

from __future__ import annotations

import logging
import re
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from math_variant.events import ROLE_TO_STAGE, EventStage, PipelineEvent, summarize_response
from math_variant.providers.base import LLMProvider, ModelPolicy
from math_variant.providers.contracts import (
    ProviderError,
    ProviderErrorCode,
    ProviderResponse,
    StructuredRequest,
)
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.resolver import RoleResolver

_SECRET_PATTERN = re.compile(r"(sk-[A-Za-z0-9_\-]{6,}|AIza[A-Za-z0-9_\-]{6,}|[A-Za-z0-9_\-]{32,})")


def redact_secrets(text: str) -> str:
    """로그에서 API 키류 문자열을 마스킹한다."""
    return _SECRET_PATTERN.sub("***", text)


class StructuredOutputEngine:
    """구조화 생성 요청을 실행하는 오케스트레이터."""

    def __init__(
        self,
        primary: LLMProvider | None,
        fallback: LLMProvider | None,
        schemas: SchemaRegistry,
        max_repair_attempts: int = 1,
        logger: logging.Logger | None = None,
        role_resolver: RoleResolver | None = None,
        on_event: Callable[[PipelineEvent], None] | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.schemas = schemas
        self.max_repair_attempts = max(0, min(1, max_repair_attempts))
        self.logger = logger or logging.getLogger("math_variant.providers")
        self.role_resolver = role_resolver
        self.on_event = on_event
        self._event_seq = 0
        self._event_lock = threading.Lock()

    def generate_structured(
        self,
        request: StructuredRequest,
        policy: ModelPolicy | None,
    ) -> ProviderResponse:
        provider: LLMProvider | None
        fallback: LLMProvider | None
        resolved_policy: ModelPolicy | None
        if self.role_resolver is not None:
            provider = self.role_resolver.provider_for(request.role)
            fallback = self.role_resolver.fallback_for(request.role)
            resolved_policy = policy or self.role_resolver.policy_for(request.role)
        else:
            provider = self.primary
            fallback = self.fallback
            resolved_policy = policy

        if provider is None or resolved_policy is None:
            return ProviderResponse(
                request_id=request.request_id,
                ok=False,
                error=ProviderError(
                    code=ProviderErrorCode.INFRA_ERROR,
                    message="역할 정책 또는 공급자가 설정되지 않았다",
                ),
            )

        fallback_used = False
        repair_used = 0
        attempts = 0
        last_error: ProviderError | None = None
        latency = 0
        cost = 0.0
        final_provider: str | None = None

        while provider is not None:
            attempts += 1
            prompt = request.prompt
            if repair_used > 0 and last_error is not None:
                prompt = self._repair_prompt(request.prompt, last_error)

            self.logger.info(
                "provider_attempt",
                extra={
                    "request_id": request.request_id,
                    "role": request.role.value,
                    "provider": provider.name,
                    "attempt": attempts,
                    "prompt_chars": len(prompt),
                },
            )
            try:
                completion = provider.complete(prompt, resolved_policy)
            except Exception as exc:
                last_error = ProviderError(
                    code=ProviderErrorCode.INFRA_ERROR,
                    message=f"공급자 호출 실패: {provider.name}",
                    detail=redact_secrets(str(exc))[:300],
                    provider=provider.name,
                    attempt=attempts,
                )
            else:
                latency += completion.latency_ms
                cost += completion.cost_usd
                final_provider = completion.provider
                data, parse_error = self.schemas.parse(request.response_schema, completion.raw_text)
                if data is not None:
                    self.logger.info(
                        "structured_ok",
                        extra={
                            "request_id": request.request_id,
                            "schema": request.response_schema,
                            "attempt": attempts,
                            "provider": final_provider,
                        },
                    )
                    self._emit_llm_call(
                        request,
                        resolved_policy,
                        ok=True,
                        data=data,
                        final_provider=final_provider,
                        attempts=attempts,
                        latency=latency,
                        cost=cost,
                        error=None,
                    )
                    return ProviderResponse(
                        request_id=request.request_id,
                        ok=True,
                        data=data,
                        provider=final_provider,
                        model_policy=resolved_policy.model,
                        attempts=attempts,
                        latency_ms=latency,
                        cost_usd=cost,
                    )
                last_error = parse_error
                if last_error is not None:
                    last_error = last_error.model_copy(
                        update={"provider": final_provider, "attempt": attempts}
                    )

            # 복구는 primary(resolver 포함) 에 대해 1회, 폴백은 한 번만.
            if (
                repair_used < self.max_repair_attempts
                and not fallback_used
                and provider is not fallback
            ):
                repair_used += 1
                continue
            if not fallback_used and request.allow_fallback and fallback is not None:
                fallback_used = True
                provider = fallback
                continue
            break

        if last_error is None:
            last_error = ProviderError(
                code=ProviderErrorCode.INFRA_ERROR, message="구조화 생성 실패"
            )

        self.logger.warning(
            "structured_failed",
            extra={
                "request_id": request.request_id,
                "code": last_error.code.value,
                "attempts": attempts,
                "recovered": fallback_used or repair_used > 0,
            },
        )
        self._emit_llm_call(
            request,
            resolved_policy,
            ok=False,
            data=None,
            final_provider=final_provider,
            attempts=attempts,
            latency=latency,
            cost=cost,
            error=last_error,
        )
        return ProviderResponse(
            request_id=request.request_id,
            ok=False,
            error=last_error,
            provider=final_provider,
            attempts=attempts,
            latency_ms=latency,
            cost_usd=cost,
        )

    def _emit_llm_call(
        self,
        request: StructuredRequest,
        policy: ModelPolicy,
        *,
        ok: bool,
        data: dict[str, Any] | None,
        final_provider: str | None,
        attempts: int,
        latency: int,
        cost: float,
        error: ProviderError | None,
    ) -> None:
        if self.on_event is None:
            return
        with self._event_lock:
            self._event_seq += 1
            seq = self._event_seq
        event = PipelineEvent(
            event_id=f"llm-{seq}",
            type="llm_call",
            stage=ROLE_TO_STAGE.get(request.role.value, EventStage.DONE),
            status="done" if ok else "failed",
            ts=datetime.now(UTC),
            data={
                "role": request.role.value,
                "schema": request.response_schema,
                "provider": final_provider
                or (error.provider if error else None)
                or policy.provider,
                "model": policy.model,
                "temperature": policy.temperature,
                "attempts": attempts,
                "latency_ms": latency,
                "cost_usd": cost,
                "ok": ok,
                "summary": summarize_response(request.response_schema, data or {}),
                "error": self._redact_error(error) if error else None,
            },
        )
        self.on_event(event)

    @staticmethod
    def _redact_error(error: ProviderError) -> dict[str, Any]:
        return {
            **error.model_dump(),
            "detail": redact_secrets(error.detail),
            "message": redact_secrets(error.message),
        }

    @staticmethod
    def _repair_prompt(original: str, error: ProviderError) -> str:
        return (
            f"{original}\n\n"
            "[시스템] 이전 응답이 검증에 실패했습니다. "
            f"오류: {error.code.value}: {error.message} {error.detail}\n"
            "반드시 요청된 JSON 스키마만 다시 출력하세요."
        )

"""LangChain 역할 체인 엔진 — 재시도·복구·비용 계측 및 이벤트 발행 지원.

기존 에이전트(Planner/Ideator/Selector/Generator/CodeReview/Critic/Judge/Blind/
Vision)는 `generate_structured(request, policy)` 계약에만 의존하므로, 이 엔진으로
엔진만 교체하면 에이전트·프롬프트 조립 코드를 전혀 수정하지 않고 LLM 호출
계층을 httpx → LangChain 체인으로 갈아끼울 수 있다.

기존 StructuredOutputEngine 과 동일하게:
1. DeepSeek 일시적 인프라 오류 / 빈 응답 시 최대 N 회 재시도 (transient_retry)
2. 스키마 파싱 오류 시 _repair_prompt 주입 후 1회 자가 복구 (repair_used)
3. primary 실패 시 fallback 체인 자동 전환 (allow_fallback)
4. total_tokens 기반 cost_usd 및 latency_ms 계측
5. on_event 콜백을 통한 llm_call 이벤트 발행
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from math_variant.events import PipelineEvent
from math_variant.providers.base import ModelPolicy
from math_variant.providers.contracts import (
    ProviderError,
    ProviderErrorCode,
    ProviderResponse,
    RolePolicy,
    StructuredRequest,
)
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import (
    _TRANSIENT_ERROR_CODES,
    StructuredOutputEngine,
    redact_secrets,
)

_LOGGER = logging.getLogger("math_variant.langchain_generator.engine")


class LangChainRoleEngine(StructuredOutputEngine):
    """역할별 구조화 체인으로 요청을 실행하고 재시도·복구·계측을 제공하는 LangChain 엔진."""

    def __init__(
        self,
        chains: dict[RolePolicy, Runnable[dict[str, str], Any]],
        fallback_chains: dict[RolePolicy, Runnable[dict[str, str], Any]] | None = None,
        max_transient_retries: int = 7,
        max_repair_attempts: int = 1,
        on_event: Callable[[PipelineEvent], None] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(
            primary=None,
            fallback=None,
            schemas=SchemaRegistry(),
            max_repair_attempts=max_repair_attempts,
            max_transient_retries=max_transient_retries,
            on_event=on_event,
            logger=logger or _LOGGER,
        )
        self._chains = chains
        self._fallback_chains = fallback_chains or {}

    def generate_structured(
        self, request: StructuredRequest, policy: ModelPolicy | None
    ) -> ProviderResponse:
        """요청의 역할에 해당하는 체인을 호출해 구조화 응답을 반환한다 (재시도·복구·폴백 포함)."""
        active_chains = self._chains
        fallback_used = False
        repair_used = 0
        transient_retries = 0
        attempts = 0
        last_error: ProviderError | None = None
        latency = 0
        cost = 0.0
        final_provider: str | None = None

        while True:
            chain = active_chains.get(request.role)
            if chain is None:
                self.logger.warning("chain_missing", extra={"role": request.role.value})
                last_error = ProviderError(
                    code=ProviderErrorCode.INFRA_ERROR,
                    message=f"역할에 대한 LangChain 체인이 설정되지 않았다: {request.role.value}",
                )
                break

            attempts += 1
            prompt = request.prompt
            if repair_used > 0 and last_error is not None:
                prompt = self._repair_prompt(request.prompt, last_error)

            self.logger.info(
                "langchain_attempt",
                extra={
                    "request_id": request.request_id,
                    "role": request.role.value,
                    "attempt": attempts,
                    "prompt_chars": len(prompt),
                    "fallback_used": fallback_used,
                    "repair_used": repair_used,
                },
            )

            start_time = time.perf_counter()
            try:
                output = chain.invoke({"input": prompt})
            except Exception as exc:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                latency += elapsed_ms
                # 기존 StructuredOutputEngine 과 동일하게, 공급자 호출 예외는
                # 종류를 가리지 않고 INFRA_ERROR(일시적) 로 취급한다. 파싱·검증
                # 오류의 구분은 아래 include_raw 응답 분기에서 타입 기반으로 한다.
                last_error = ProviderError(
                    code=ProviderErrorCode.INFRA_ERROR,
                    message=f"LangChain 체인 실행 실패 ({request.role.value})",
                    detail=redact_secrets(str(exc))[:300],
                    attempt=attempts,
                )
            else:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                latency += elapsed_ms

                parsed_data: Any = None
                raw_msg: Any = None
                parsing_err: Any = None

                if isinstance(output, dict) and ("parsed" in output or "raw" in output):
                    parsed_data = output.get("parsed")
                    raw_msg = output.get("raw")
                    parsing_err = output.get("parsing_error")
                elif isinstance(output, BaseModel):
                    parsed_data = output
                else:
                    parsed_data = output

                if raw_msg is not None:
                    usage = getattr(raw_msg, "usage_metadata", None)
                    if not usage and hasattr(raw_msg, "response_metadata"):
                        usage = raw_msg.response_metadata.get("token_usage")
                    if isinstance(usage, dict):
                        total_tokens = usage.get("total_tokens", 0)
                        cost += float(total_tokens) / 1_000_000
                    resp_meta = getattr(raw_msg, "response_metadata", {})
                    final_provider = resp_meta.get("model_name") or "langchain"

                if parsed_data is not None:
                    data: dict[str, Any]
                    if isinstance(parsed_data, BaseModel):
                        data = parsed_data.model_dump(mode="json")
                    elif isinstance(parsed_data, dict):
                        data = parsed_data
                    else:
                        data = {"output": str(parsed_data)}

                    self.logger.info(
                        "langchain_structured_ok",
                        extra={
                            "request_id": request.request_id,
                            "role": request.role.value,
                            "attempt": attempts,
                            "latency_ms": latency,
                            "cost_usd": cost,
                        },
                    )
                    self._emit_llm_call(
                        request,
                        policy or ModelPolicy(provider="langchain", model=final_provider or "chat"),
                        ok=True,
                        data=data,
                        final_provider=final_provider or "langchain",
                        attempts=attempts,
                        latency=latency,
                        cost=cost,
                        error=None,
                    )
                    return ProviderResponse(
                        request_id=request.request_id,
                        ok=True,
                        data=data,
                        provider=final_provider or "langchain",
                        model_policy=policy.model if policy else final_provider,
                        attempts=attempts,
                        latency_ms=latency,
                        cost_usd=cost,
                    )

                # 파싱 실패 분류 — 기존 SchemaRegistry.parse 와 동일한 기준:
                # 빈 응답 → EMPTY_RESPONSE(재시도), JSON 수준 오류 → TRUNCATED_JSON
                # (재시도), Pydantic 검증 실패 → SCHEMA_VALIDATION(복구 프롬프트 대상).
                raw_content = str(getattr(raw_msg, "content", "") or "").strip()
                if not raw_content:
                    err_code = ProviderErrorCode.EMPTY_RESPONSE
                elif isinstance(parsing_err, OutputParserException):
                    err_code = ProviderErrorCode.TRUNCATED_JSON
                else:
                    err_code = ProviderErrorCode.SCHEMA_VALIDATION
                err_detail = (
                    redact_secrets(str(parsing_err))[:300]
                    if parsing_err
                    else "결과 모델 검증 실패"
                )
                last_error = ProviderError(
                    code=err_code,
                    message="LangChain 구조화 출력 파싱 실패",
                    detail=err_detail,
                    attempt=attempts,
                )

            # 일시적 오류 재시도 (빈 응답, 인프라 에러 등)
            if (
                last_error is not None
                and last_error.code in _TRANSIENT_ERROR_CODES
                and transient_retries < self.max_transient_retries
            ):
                transient_retries += 1
                self.logger.info(
                    "langchain_transient_retry",
                    extra={
                        "request_id": request.request_id,
                        "code": last_error.code.value,
                        "retry": transient_retries,
                    },
                )
                continue

            # 스키마 복구 프롬프트 주입 재시도 (1회)
            if (
                last_error is not None
                and last_error.code not in _TRANSIENT_ERROR_CODES
                and repair_used < self.max_repair_attempts
                and not fallback_used
            ):
                repair_used += 1
                self.logger.info(
                    "langchain_schema_repair",
                    extra={"request_id": request.request_id, "repair_attempt": repair_used},
                )
                continue

            # Fallback 체인 전환
            if (
                not fallback_used
                and request.allow_fallback
                and self._fallback_chains.get(request.role) is not None
            ):
                fallback_used = True
                active_chains = self._fallback_chains
                self.logger.info(
                    "langchain_fallback_switch",
                    extra={"request_id": request.request_id, "role": request.role.value},
                )
                continue

            break

        if last_error is None:
            last_error = ProviderError(
                code=ProviderErrorCode.INFRA_ERROR, message="LangChain 구조화 생성 실패"
            )

        self.logger.warning(
            "langchain_structured_failed",
            extra={
                "request_id": request.request_id,
                "code": last_error.code.value,
                "attempts": attempts,
                "recovered": fallback_used or repair_used > 0,
            },
        )
        self._emit_llm_call(
            request,
            policy or ModelPolicy(provider="langchain", model=final_provider or "chat"),
            ok=False,
            data=None,
            final_provider=final_provider or "langchain",
            attempts=attempts,
            latency=latency,
            cost=cost,
            error=last_error,
        )
        return ProviderResponse(
            request_id=request.request_id,
            ok=False,
            error=last_error,
            provider=final_provider or "langchain",
            attempts=attempts,
            latency_ms=latency,
            cost_usd=cost,
        )

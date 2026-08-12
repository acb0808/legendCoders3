"""T02.3 — LLM 공급자 어댑터와 구조화 출력 계약 테스트.

- T02.3-CT1: 유효 JSON 은 해당 Pydantic 모델로 파싱된다.
- T02.3-CT2: 빈 응답·잘린 JSON·추가 필드가 각각 구조화된 오류가 된다.
- T02.3-CT3: 복구 1회 실패 후 폴백 1회만 호출된다.
- T02.3-CT4: 공급자 로그에 키·전체 민감 프롬프트가 남지 않는다.
- T02.3-CT5: 역할 정책 변경은 비즈니스 코드 수정 없이 설정만 바꾼다.
"""

from __future__ import annotations

import logging

import pytest
from pydantic import BaseModel, ConfigDict

from math_variant.providers.base import ModelPolicy, RawCompletion
from math_variant.providers.contracts import (
    ProviderErrorCode,
    RolePolicy,
    StructuredRequest,
)
from math_variant.providers.registry import SchemaRegistry
from math_variant.providers.structured import StructuredOutputEngine


class TangentAnalysis(BaseModel):
    """골드/테스트용 응답 스키마 (추가 필드는 거부)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    center: str
    radius: str
    line: str
    parameter: str | None = None
    goal: str


def _registry() -> SchemaRegistry:
    reg = SchemaRegistry()
    reg.register(TangentAnalysis)
    return reg


class FakeProvider:
    """테스트 전용 LLMProvider (네트워크 없음)."""

    def __init__(self, name: str, responses: list[str] | None = None) -> None:
        self.name = name
        self.responses = list(responses or [])
        self.calls: list[str] = []

    def complete(self, prompt: str, policy: ModelPolicy) -> RawCompletion:
        self.calls.append(prompt)
        raw = self.responses.pop(0) if self.responses else "{}"
        return RawCompletion(
            raw_text=raw, latency_ms=10, cost_usd=0.0, provider=self.name, model=policy.model
        )


def _policy(provider: str = "fake-a", model: str = "test-model") -> ModelPolicy:
    return ModelPolicy(provider=provider, model=model)


def test_ct1_valid_json_parses_to_model() -> None:
    payload = {
        "center": "(0,0)",
        "radius": "2",
        "line": "y = 2x + 1",
        "parameter": "k",
        "goal": "접선의 방정식",
    }
    engine = StructuredOutputEngine(
        primary=FakeProvider("fake-a", [__import__("json").dumps(payload)]),
        fallback=None,
        schemas=_registry(),
    )
    response = engine.generate_structured(
        StructuredRequest(
            request_id="r1",
            role=RolePolicy.SOURCE_ANALYZER,
            prompt="분석해라",
            response_schema="TangentAnalysis",
        ),
        _policy(),
    )

    assert response.ok is True
    assert response.data == TangentAnalysis(**payload).model_dump()
    assert response.error is None


def test_ct2_empty_truncated_extra_fields_are_structured_errors() -> None:
    cases: list[tuple[str, ProviderErrorCode]] = [
        ("", ProviderErrorCode.EMPTY_RESPONSE),
        (
            "{'center': '(0,0)', 'radius': '2', 'line': 'y=x', 'goal': 'x'",
            ProviderErrorCode.TRUNCATED_JSON,
        ),
    ]
    for raw, expected_code in cases:
        engine = StructuredOutputEngine(
            primary=FakeProvider("fake-a", [raw]),
            fallback=None,
            schemas=_registry(),
            max_repair_attempts=0,
        )
        response = engine.generate_structured(
            StructuredRequest(
                request_id="r2",
                role=RolePolicy.SOURCE_ANALYZER,
                prompt="p",
                response_schema="TangentAnalysis",
            ),
            _policy(),
        )
        assert response.ok is False
        assert response.error is not None
        assert response.error.code == expected_code

    # 추가 필드 → SCHEMA_VALIDATION
    extra_payload = {
        "center": "(0,0)",
        "radius": "2",
        "line": "y=x",
        "goal": "x",
        "injected": "extra",
    }
    engine = StructuredOutputEngine(
        primary=FakeProvider("fake-a", [__import__("json").dumps(extra_payload)]),
        fallback=None,
        schemas=_registry(),
        max_repair_attempts=0,
    )
    response = engine.generate_structured(
        StructuredRequest(
            request_id="r3",
            role=RolePolicy.SOURCE_ANALYZER,
            prompt="p",
            response_schema="TangentAnalysis",
        ),
        _policy(),
    )
    assert response.ok is False
    assert response.error is not None
    assert response.error.code == ProviderErrorCode.SCHEMA_VALIDATION
    assert "injected" in response.error.detail


def test_ct3_repair_once_then_fallback_once() -> None:
    valid = __import__("json").dumps({"center": "(0,0)", "radius": "2", "line": "y=x", "goal": "x"})
    primary = FakeProvider("primary", ["{bad json", "also bad"])  # 첫 시도 + 복구 시도 둘 다 실패
    fallback = FakeProvider("fallback", [valid])

    engine = StructuredOutputEngine(
        primary=primary,
        fallback=fallback,
        schemas=_registry(),
        max_repair_attempts=1,
    )
    response = engine.generate_structured(
        StructuredRequest(
            request_id="r4",
            role=RolePolicy.SOURCE_ANALYZER,
            prompt="p",
            response_schema="TangentAnalysis",
        ),
        _policy(),
    )

    assert response.ok is True
    assert len(primary.calls) == 2  # 첫 시도 + 복구 1회
    assert len(fallback.calls) == 1  # 폴백 1회만
    assert response.provider == "fallback"


def test_ct3_no_fallback_when_primary_succeeds() -> None:
    valid = __import__("json").dumps({"center": "(0,0)", "radius": "2", "line": "y=x", "goal": "x"})
    primary = FakeProvider("primary", [valid])
    fallback = FakeProvider("fallback", [])

    engine = StructuredOutputEngine(
        primary=primary, fallback=fallback, schemas=_registry(), max_repair_attempts=1
    )
    response = engine.generate_structured(
        StructuredRequest(
            request_id="r5",
            role=RolePolicy.SOURCE_ANALYZER,
            prompt="p",
            response_schema="TangentAnalysis",
        ),
        _policy(),
    )

    assert response.ok is True
    assert len(primary.calls) == 1
    assert len(fallback.calls) == 0


def test_ct4_logs_do_not_contain_keys_or_full_prompt(caplog: pytest.LogCaptureFixture) -> None:
    secret = "sk-ULTRA_SECRET_VALUE_123"  # noqa: S105 - 로그 차단 검증용 테스트 비밀
    full_prompt = "이것은 매우 긴 민감한 프롬프트 본문이다. 조건과 답을 포함한다."

    payload = __import__("json").dumps(
        {"center": "(0,0)", "radius": "2", "line": "y=x", "goal": "x"}
    )

    class SecretiveProvider(FakeProvider):
        def complete(self, prompt: str, policy: ModelPolicy) -> RawCompletion:
            # 공급자 내부에서 비밀을 다루는 상황을 재현 (로그에 새면 안 된다)
            logger = logging.getLogger("math_variant.providers.debug")
            logger.debug("policy=%s", policy.model_dump())
            logger.debug("call_latency=10ms")
            return super().complete(prompt, policy)

    engine = StructuredOutputEngine(
        primary=SecretiveProvider("primary", [payload]),
        fallback=None,
        schemas=_registry(),
        logger=logging.getLogger("math_variant.providers"),
    )
    with caplog.at_level(logging.DEBUG, logger="math_variant.providers"):
        response = engine.generate_structured(
            StructuredRequest(
                request_id="r6",
                role=RolePolicy.SOURCE_ANALYZER,
                prompt=full_prompt,
                response_schema="TangentAnalysis",
                api_key_guard=secret,  # 요청 계약에 실수로 포함된 비밀
            ),
            _policy(),
        )
        assert response.ok is True

    joined = "\n".join(rec.getMessage() for rec in caplog.records)
    assert secret not in joined
    assert full_prompt not in joined


def test_ct5_role_policy_change_via_config_only() -> None:
    from math_variant.providers.resolver import RolePolicyConfig, RoleResolver

    payload = __import__("json").dumps(
        {"center": "(0,0)", "radius": "2", "line": "y=x", "goal": "x"}
    )

    providers: dict[str, FakeProvider] = {
        "openai": FakeProvider("openai", [payload]),
        "deepseek": FakeProvider("deepseek", [payload]),
    }

    config_a = RolePolicyConfig(
        roles={RolePolicy.SOURCE_ANALYZER: {"provider": "openai", "model": "gpt-5-mini"}}
    )
    config_b = RolePolicyConfig(
        roles={RolePolicy.SOURCE_ANALYZER: {"provider": "deepseek", "model": "deepseek-chat"}}
    )

    def resolve_engine(config: RolePolicyConfig) -> StructuredOutputEngine:
        resolver = RoleResolver(config, providers)
        engine = StructuredOutputEngine(
            primary=None,  # type: ignore[arg-type]  # resolver 가 제공
            fallback=None,
            schemas=_registry(),
        )
        engine.role_resolver = resolver
        return engine

    engine_a = resolve_engine(config_a)
    response_a = engine_a.generate_structured(
        StructuredRequest(
            request_id="r7",
            role=RolePolicy.SOURCE_ANALYZER,
            prompt="p",
            response_schema="TangentAnalysis",
        ),
        policy=None,  # type: ignore[arg-type]
    )
    engine_b = resolve_engine(config_b)
    response_b = engine_b.generate_structured(
        StructuredRequest(
            request_id="r8",
            role=RolePolicy.SOURCE_ANALYZER,
            prompt="p",
            response_schema="TangentAnalysis",
        ),
        policy=None,  # type: ignore[arg-type]
    )

    # 설정만 바꿨을 뿐, 호출하는 비즈니스 코드는 동일하다.
    assert response_a.provider == "openai"
    assert response_b.provider == "deepseek"


def test_ct5_role_resolver_repair_once_on_resolved_primary() -> None:
    """역할 리졸버가 공급자를 줄 때에도 복구 1회가 동작한다.

    primary=None 인 엔진에서 역할 리졸버의 provider_for 가 해석한 공급자가
    먼저 잘못된 JSON 을 반환해도 복구 시도(2번째 호출)에서 성공해야 한다.
    """
    from math_variant.providers.resolver import RolePolicyConfig, RoleResolver

    valid = __import__("json").dumps({"center": "(0,0)", "radius": "2", "line": "y=x", "goal": "x"})
    provider = FakeProvider("openai", ["{bad json", valid])

    config = RolePolicyConfig(
        roles={RolePolicy.SOURCE_ANALYZER: {"provider": "openai", "model": "gpt-5-mini"}}
    )
    resolver = RoleResolver(config, {"openai": provider})
    engine = StructuredOutputEngine(
        primary=None,  # type: ignore[arg-type]  # resolver 가 제공
        fallback=None,
        schemas=_registry(),
        max_repair_attempts=1,
    )
    engine.role_resolver = resolver

    response = engine.generate_structured(
        StructuredRequest(
            request_id="r9",
            role=RolePolicy.SOURCE_ANALYZER,
            prompt="p",
            response_schema="TangentAnalysis",
        ),
        policy=None,  # type: ignore[arg-type]
    )

    assert response.ok is True
    assert len(provider.calls) == 2  # 첫 시도 + 복구 1회
    assert response.provider == "openai"
    assert response.attempts == 2

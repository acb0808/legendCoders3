"""다중 에이전트 역할 정책 기본값·재정의 테스트."""

from __future__ import annotations

import pytest

from math_variant.errors import MathVariantError
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.settings import ProviderSettings

TEXT_ROLES = {
    RolePolicy.SOURCE_ANALYZER,
    RolePolicy.GENERATOR,
    RolePolicy.BLIND_SOLVER,
    RolePolicy.CRITIC,
    RolePolicy.PLANNER,
    RolePolicy.IDEATOR,
    RolePolicy.SELECTOR,
    RolePolicy.CODE_REVIEWER,
    RolePolicy.JUDGE,
}


def test_text_roles_default_to_deepseek_flash() -> None:
    roles = ProviderSettings(_env_file=None).role_policy().roles
    for role in TEXT_ROLES:
        assert roles[role].provider == "deepseek"
        assert roles[role].model == "deepseek-v4-flash"  # deepseek_model_flash 기본값


def test_roles_have_no_temperature() -> None:
    """온도는 사용하지 않는다 — deepseek-v4-flash 는 온도를 보내면 빈 응답이 잦고,
    gpt-5.6-luna 는 온도를 지원하지 않는다."""
    roles = ProviderSettings(_env_file=None).role_policy().roles
    assert len(roles) == len(RolePolicy)
    for role in roles:
        assert not hasattr(roles[role], "temperature")


def test_vision_role_uses_luna_provider() -> None:
    roles = ProviderSettings(_env_file=None).role_policy().roles
    vision = roles[RolePolicy.VISION]
    assert vision.provider == "openai"
    assert vision.model == "gpt-5.6-luna"


def test_role_policy_json_override_for_new_role() -> None:
    settings = ProviderSettings(
        _env_file=None,
        role_policy_json='{"ideator": {"provider": "openai", "model": "gpt-5.6-luna"}}',
    )
    entry = settings.role_policy().roles[RolePolicy.IDEATOR]
    assert entry.provider == "openai"
    assert entry.model == "gpt-5.6-luna"


def test_json_override_merges_over_defaults() -> None:
    settings = ProviderSettings(
        _env_file=None,
        role_policy_json='{"ideator": {"provider": "openai", "model": "gpt-5.6-luna"}}',
    )
    roles = settings.role_policy().roles
    assert roles[RolePolicy.SOURCE_ANALYZER].provider == "deepseek"
    assert roles[RolePolicy.VISION].provider == "openai"
    assert roles[RolePolicy.VISION].model == "gpt-5.6-luna"


def test_invalid_json_raises_parse_rejected() -> None:
    settings = ProviderSettings(_env_file=None, role_policy_json="{bad json")
    with pytest.raises(MathVariantError) as exc_info:
        settings.role_policy()
    assert exc_info.value.code == "PARSE_REJECTED"


def test_unknown_role_raises_parse_rejected() -> None:
    settings = ProviderSettings(_env_file=None, role_policy_json='{"not_a_role": {}}')
    with pytest.raises(MathVariantError) as exc_info:
        settings.role_policy()
    assert exc_info.value.code == "PARSE_REJECTED"

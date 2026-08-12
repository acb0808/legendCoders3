"""다중 에이전트 역할 정책 기본값·재정의 테스트."""

from __future__ import annotations

import pytest

from math_variant.errors import MathVariantError
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.settings import ProviderSettings

EXPECTED_DEFAULT_TEMPERATURES = {
    RolePolicy.SOURCE_ANALYZER: 0.2,
    RolePolicy.GENERATOR: 0.7,
    RolePolicy.BLIND_SOLVER: 0.2,
    RolePolicy.CRITIC: 0.2,
    RolePolicy.PLANNER: 0.2,
    RolePolicy.IDEATOR: 1.4,
    RolePolicy.SELECTOR: 0.3,
    RolePolicy.CODE_REVIEWER: 0.2,
    RolePolicy.JUDGE: 0.2,
    RolePolicy.VISION: 0.4,
}


def test_default_roles_include_new_agents_with_high_ideator_temperature() -> None:
    roles = ProviderSettings(_env_file=None).role_policy().roles
    assert roles[RolePolicy.PLANNER].provider == "deepseek"
    assert roles[RolePolicy.IDEATOR].temperature == 1.4
    assert roles[RolePolicy.SELECTOR].temperature == 0.3
    assert roles[RolePolicy.CODE_REVIEWER].temperature == 0.2
    assert roles[RolePolicy.JUDGE].temperature == 0.2
    assert roles[RolePolicy.GENERATOR].temperature == 0.7


def test_vision_role_uses_luna_provider() -> None:
    roles = ProviderSettings(_env_file=None).role_policy().roles
    vision = roles[RolePolicy.VISION]
    assert vision.provider == "openai"
    assert vision.model == "gpt-5.6-luna"


def test_text_roles_default_to_deepseek_flash_model() -> None:
    roles = ProviderSettings(_env_file=None).role_policy().roles
    for role in (
        RolePolicy.PLANNER,
        RolePolicy.IDEATOR,
        RolePolicy.SELECTOR,
        RolePolicy.CODE_REVIEWER,
        RolePolicy.JUDGE,
    ):
        assert roles[role].model == "deepseek-chat"  # deepseek_model_flash 기본값


def test_all_roles_have_expected_default_temperatures() -> None:
    roles = ProviderSettings(_env_file=None).role_policy().roles
    assert len(roles) == len(RolePolicy)
    for role, temperature in EXPECTED_DEFAULT_TEMPERATURES.items():
        assert roles[role].temperature == temperature


def test_role_policy_json_override_for_new_role() -> None:
    settings = ProviderSettings(
        _env_file=None,
        role_policy_json=(
            '{"ideator": {"provider": "openai", "model": "gpt-5.6-luna", "temperature": 1.6}}'
        ),
    )
    entry = settings.role_policy().roles[RolePolicy.IDEATOR]
    assert entry.provider == "openai"
    assert entry.model == "gpt-5.6-luna"
    assert entry.temperature == 1.6


def test_json_override_merges_over_defaults() -> None:
    settings = ProviderSettings(
        _env_file=None,
        role_policy_json=(
            '{"ideator": {"provider": "openai", "model": "gpt-5.6-luna", "temperature": 1.6}}'
        ),
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

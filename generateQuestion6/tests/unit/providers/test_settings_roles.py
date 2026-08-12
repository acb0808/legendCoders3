"""다중 에이전트 역할 정책 기본값·재정의 테스트."""

from __future__ import annotations

from math_variant.providers.contracts import RolePolicy
from math_variant.providers.settings import ProviderSettings


def test_default_roles_include_new_agents_with_high_ideator_temperature() -> None:
    roles = ProviderSettings(_env_file=None).role_policy().roles
    assert roles[RolePolicy.PLANNER].provider == "deepseek"
    assert roles[RolePolicy.IDEATOR].temperature >= 1.3
    assert roles[RolePolicy.SELECTOR].temperature < 1.0
    assert roles[RolePolicy.CODE_REVIEWER].temperature <= 0.3
    assert roles[RolePolicy.JUDGE].temperature <= 0.3
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

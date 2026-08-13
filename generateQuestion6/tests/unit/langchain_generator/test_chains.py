"""LangChain 구조화 체인 테스트 — 네트워크 호출 없이 구성만 검증한다."""

from __future__ import annotations

from typing import cast

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.base import RunnableSequence
from langchain_openai import ChatOpenAI

from math_variant.agents.schemas import PlannerOutput
from math_variant.langchain_generator.chains import JSON_SYSTEM_MESSAGE, build_structured_chain


def _fake_llm() -> ChatOpenAI:
    """네트워크를 호출하지 않는 ChatOpenAI 인스턴스 (생성만 한다)."""
    return ChatOpenAI(
        model="deepseek-chat",
        api_key="test-key",
        base_url="https://example.invalid/v1",
        temperature=None,
    )


def test_structured_chain_binds_output_schema() -> None:
    """체인의 output_schema 가 요청한 Pydantic 모델을 그대로 노출해야 한다."""
    chain = build_structured_chain(
        _fake_llm(), system_md="기획자 역할 프롬프트", output_model=PlannerOutput
    )
    assert chain.output_schema == PlannerOutput


def test_system_message_injects_json_instruction_and_role_md() -> None:
    """시스템 메시지에 JSON 지시와 역할 프롬프트 본문이 모두 포함되어야 한다."""
    role_md = '기획자 역할 프롬프트 본문 (planner.md 재사용) — 예시 {"dimension": "objective"}'
    chain = build_structured_chain(
        _fake_llm(), system_md=role_md, output_model=PlannerOutput
    )
    seq = cast(RunnableSequence[dict[str, str], PlannerOutput], chain)
    template = cast(ChatPromptTemplate, seq.first)
    assert template.input_variables == ["input"]

    messages = template.format_messages(input="입력 문자열")
    assert isinstance(messages[0], SystemMessage)
    system = str(messages[0].content)
    assert JSON_SYSTEM_MESSAGE in system
    assert role_md in system
    assert system.index(JSON_SYSTEM_MESSAGE) < system.index(role_md)

    assert isinstance(messages[1], HumanMessage)
    assert str(messages[1].content) == "입력 문자열"


def test_real_prompt_md_files_build_without_template_errors() -> None:
    """기존 프롬프트 md(JSON 예시 중괄호 포함)로 세 역할 체인을 모두 빌드할 수 있어야 한다."""
    from pathlib import Path

    from math_variant.agents.schemas import GeneratorOutput, IdeationOutput
    from math_variant.langchain_generator.generator import PROMPTS_DIR

    prompts_dir = Path(PROMPTS_DIR)
    cases = [
        ("planner.md", PlannerOutput),
        ("ideator.md", IdeationOutput),
        ("candidate_generator.md", GeneratorOutput),
    ]
    for name, schema in cases:
        chain = build_structured_chain(
            _fake_llm(),
            system_md=(prompts_dir / name).read_text(encoding="utf-8"),
            output_model=schema,
        )
        assert chain.output_schema == schema


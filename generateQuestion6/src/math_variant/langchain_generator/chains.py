"""LangChain LCEL 체인 — 기존 프롬프트(md)·Pydantic 스키마를 재사용한다.

역할별 체인은 (system: JSON 지시 + 역할 프롬프트) + (human: 구조화 입력) 로 구성하고,
`ChatOpenAI.with_structured_output(method="json_mode")` 로 Pydantic 모델에 바인딩한다.
"""

from __future__ import annotations

from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

JSON_SYSTEM_MESSAGE = "You must respond in JSON format only."


def build_structured_chain[T: BaseModel](
    llm: ChatOpenAI,
    *,
    system_md: str,
    output_model: type[T],
    include_raw: bool = False,
) -> Runnable[dict[str, str], Any]:
    """역할 프롬프트 + JSON 지시를 시스템에, 입력을 human 에 넣는 구조화 체인을 만든다.

    DeepSeek 는 response_format=json_object 사용 시 프롬프트에 "json" 단어가 있어야
    400 을 반환하지 않으므로, 시스템 메시지에 JSON 응답 지시를 항상 주입한다
    (기존 `openai_adapter` 와 동일한 전략).
    기존 프롬프트 md 에는 JSON 예시의 중괄호가 들어 있으므로, f-string 대신
    mustache 템플릿 형식을 사용해 리터럴 중괄호를 그대로 보존한다.
    `include_raw=True` 설정 시 `{"raw": AIMessage, "parsed": T, "parsing_error": ...}` 를 반환한다.
    """
    template = ChatPromptTemplate.from_messages(
        [
            ("system", f"{JSON_SYSTEM_MESSAGE}\n\n{system_md}"),
            ("human", "{{input}}"),
        ],
        template_format="mustache",
    )
    structured = llm.with_structured_output(
        output_model, method="json_mode", include_raw=include_raw
    )
    return cast(Runnable[dict[str, str], Any], template | structured)


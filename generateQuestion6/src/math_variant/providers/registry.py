"""응답 스키마 레지스트리 — 이름으로 Pydantic 모델을 찾는다."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from math_variant.errors import ErrorCode, MathVariantError, StructuredError
from math_variant.providers.contracts import ProviderError, ProviderErrorCode


class SchemaRegistry:
    """스키마 이름 → Pydantic 모델 클래스 매핑."""

    def __init__(self) -> None:
        self._models: dict[str, type[BaseModel]] = {}

    def register(self, model: type[BaseModel]) -> None:
        self._models[model.__name__] = model

    def register_module(self, module: object) -> None:
        """모듈에 정의된 BaseModel 하위 타입을 등록한다."""
        for name, obj in vars(module).items():
            if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel:
                self._models[name] = obj

    def resolve(self, schema_name: str) -> type[BaseModel]:
        try:
            return self._models[schema_name]
        except KeyError as exc:
            raise MathVariantError(
                StructuredError(
                    code=ErrorCode.PARSE_REJECTED,
                    message=f"등록되지 않은 응답 스키마: {schema_name}",
                    context={"schema": schema_name},
                )
            ) from exc

    def parse(
        self, schema_name: str, raw_text: str
    ) -> tuple[dict[str, Any] | None, ProviderError | None]:
        """원시 텍스트를 해당 스키마로 검증한다.

        빈 응답·잘린 JSON·추가 필드를 각각 구조화된 오류로 구분한다. (T02.3-CT2)
        """
        model = self.resolve(schema_name)
        stripped = raw_text.strip()
        if not stripped:
            return None, ProviderError(
                code=ProviderErrorCode.EMPTY_RESPONSE,
                message="공급자가 빈 응답을 반환했다",
            )
        try:
            payload = __import__("json").loads(stripped)
        except (ValueError, TypeError) as exc:
            code = ProviderErrorCode.TRUNCATED_JSON
            detail = f"JSON 파싱 실패: {str(exc)[:200]}"
            return None, ProviderError(
                code=code, message="잘린 JSON 또는 잘못된 JSON", detail=detail
            )
        try:
            instance = model.model_validate(payload)
        except Exception as exc:
            detail_lines = [str(e).replace("\n", " ") for e in getattr(exc, "errors", lambda: [])()]
            return None, ProviderError(
                code=ProviderErrorCode.SCHEMA_VALIDATION,
                message="응답이 스키마 검증에 실패했다",
                detail="; ".join(detail_lines[:5]) if detail_lines else str(exc)[:300],
            )
        return instance.model_dump(), None

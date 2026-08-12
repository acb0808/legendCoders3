"""도형 렌더러 — VISION(gpt-5.6-luna)으로 TikZ 코드를 생성해 파일로 저장한다 (T07)."""

from __future__ import annotations

import re
from pathlib import Path

from math_variant.agents._common import request_structured
from math_variant.agents.schemas import VisionOutput
from math_variant.providers.contracts import RolePolicy
from math_variant.providers.structured import StructuredOutputEngine

_FENCE_OPEN = re.compile(r"^```[a-zA-Z0-9_\-]*\s*$", re.MULTILINE)


def _strip_code_fence(tikz_code: str) -> str:
    """TikZ 코드에서 마크다운 펜스를 제거한다 (```python``` 등)."""
    text = tikz_code.strip()
    text = _FENCE_OPEN.sub("", text)
    return text.strip("`").strip()


class VisionArtist:
    """VISION 역할을 호출해 후보의 도형을 TikZ 로 렌더링한다."""

    def __init__(
        self, engine: StructuredOutputEngine, prompt_bundle: str, figures_dir: Path
    ) -> None:
        self.engine = engine
        self.prompt_bundle = prompt_bundle
        self.figures_dir = figures_dir

    def render(self, candidate_id: str, figure_notes: str, problem_text: str = "") -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", candidate_id):
            raise ValueError(f"유효하지 않은 candidate_id: {candidate_id}")
        prompt = f"{self.prompt_bundle}\n\n[문제 본문]\n{problem_text}\n[도형 설명]\n{figure_notes}"
        data = request_structured(
            self.engine,
            request_id=f"vision-{candidate_id}",
            role=RolePolicy.VISION,
            prompt=prompt,
            schema="VisionOutput",
        )
        output = VisionOutput.model_validate(data)
        return self._save(candidate_id, output)

    def _save(self, candidate_id: str, output: VisionOutput) -> Path:
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        path = self.figures_dir / f"{candidate_id}.tex"
        body = _strip_code_fence(output.tikz_code)
        caption = output.caption.replace("\n", " ")
        path.write_text(f"% figure for {candidate_id}\n% {caption}\n{body}\n", encoding="utf-8")
        return path

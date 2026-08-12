r"""원문 정규화 — 시험지 추출 텍스트(LaTeX 계열)를 파이프라인 표준형으로 변환한다.

변환 규칙 (T02.4·T02.5 가 소비하는 표준형):
- `<eq>`/`</eq>` 제거
- `\left`/`\right` 제거, `\frac{a}{b}` → `(a)/(b)`, `x^{2}` → `x^2`
- `\sqrt{...}` → `sqrt(...)`, `\cdot` → `*`
- `~` → 공백, 연속 공백 축약
"""

from __future__ import annotations

import re


def normalize_source(text: str) -> str:
    """시험지 추출 원문을 파이프라인 표준형으로 정규화한다."""
    out = text
    out = out.replace("<eq>", "").replace("</eq>", "")
    out = re.sub(r"\\left|\\right", "", out)
    out = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", out)
    out = re.sub(r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)", out)
    out = out.replace(r"\cdot", "*")
    out = re.sub(r"\^\{([^{}]+)\}", r"^\1", out)
    out = re.sub(r"_\{([^{}]+)\}", r"_\1", out)
    out = out.replace(r"\,", " ")
    out = out.replace("~", " ")
    out = out.replace("\\", "")
    out = re.sub(r"\s+", " ", out).strip()
    return out

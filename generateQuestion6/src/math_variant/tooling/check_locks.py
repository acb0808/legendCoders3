"""CI 잠금 파일 검사 엔트리포인트 (`python -m math_variant.tooling.check_locks`)."""

from __future__ import annotations

import sys
from pathlib import Path

from math_variant.tooling.quality import check_dependency_locks


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]) if args else Path.cwd()
    report = check_dependency_locks(root)
    for failure in report.failures:
        print(str(failure.as_error()), file=sys.stderr)
    if not report.ok:
        return 1
    print("의존성 잠금 파일 검사 통과")
    return 0


if __name__ == "__main__":  # pragma: no cover - 엔트리포인트
    raise SystemExit(main())

"""Vérifie que les URLs /api/ dans frontend-v51 matchent CONSUMED_API_PATH_REGEXES."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "frontend-v51"
CONSUMED_TS = FRONT / "types" / "consumed-paths.ts"
SCAN_DIRS = ("app", "components", "lib")
SKIP_PARTS = ("node_modules", "types/api.ts", "e2e/")


def _load_allowed() -> list[re.Pattern[str]]:
    raw = CONSUMED_TS.read_text(encoding="utf-8")
    found = re.findall(
        r"String\.raw`(\^(?:[^`]|\\`)+)`",
        raw,
    )
    if not found:
        raise SystemExit(f"Aucun motif trouvé dans {CONSUMED_TS}")
    return [re.compile(p) for p in found]


def _extract_urls_from_file(path: Path) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    text = path.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), start=1):
        for m in re.finditer(r"[`'\"](/api[^`'\"]+)[`'\"]", line):
            u = m.group(1)
            u = re.sub(r"\$\{[^}]+\}", ":id", u)
            out.append((u.split("?")[0], i))
    return out


def main() -> int:
    allowed = _load_allowed()
    bad: list[str] = []
    for sub in SCAN_DIRS:
        base = FRONT / sub
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            sp = str(path.relative_to(FRONT)).replace("\\", "/")
            if not sp.endswith((".ts", ".tsx")):
                continue
            if any(skip in sp for skip in SKIP_PARTS):
                continue
            for url, line in _extract_urls_from_file(path):
                if not any(p.search(url) for p in allowed):
                    bad.append(f"{sp}:{line}: {url}")
    if bad:
        print("URLs /api/ non couvertes par types/consumed-paths.ts :", file=sys.stderr)
        for b in bad:
            print(f"  {b}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

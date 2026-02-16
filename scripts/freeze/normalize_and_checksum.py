"""Normalize freeze files to LF and print SHA256 lines for SHA256SUMS.txt.
Run from repo root: python scripts/freeze/normalize_and_checksum.py
"""
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FREEZE_DIR = REPO_ROOT / "docs" / "freeze" / "v3.3.2"

FILES = [
    "CONSTITUTION_DMS_V3.3.2.md",
    "MILESTONES_EXECUTION_PLAN_V3.3.2.md",
    "INVARIANTS.md",
    "adrs/ADR-0001.md",
]

def main():
    lines = []
    for rel in FILES:
        path = FREEZE_DIR / rel
        content = path.read_bytes()
        normalized = content.replace(b"\r\n", b"\n")
        path.write_bytes(normalized)
        h = hashlib.sha256(normalized).hexdigest()
        rel_unix = rel.replace("\\", "/")
        lines.append(f"{h}  docs/freeze/v3.3.2/{rel_unix}")
    for line in lines:
        print(line)

if __name__ == "__main__":
    main()

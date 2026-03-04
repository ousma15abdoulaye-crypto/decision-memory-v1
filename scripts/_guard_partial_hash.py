"""GUARD-OPS-01 — Hash preflight/postflight de run_pipeline_a_partial.
NON COMMITÉ — contrôle opératoire local uniquement.
"""
import hashlib
import re
from pathlib import Path

src = Path("src/couche_a/pipeline/service.py").read_text(encoding="utf-8")
m = re.search(r"(^def run_pipeline_a_partial\b.*?)(?=^def |\Z)", src, re.M | re.S)

if not m:
    raise SystemExit("STOP — run_pipeline_a_partial introuvable")

bloc = m.group(1)
normalized = "\n".join(line.rstrip() for line in bloc.splitlines() if line.strip())
h = hashlib.sha256(normalized.encode()).hexdigest()
print(f"GUARD-PARTIAL-HASH={h}")
Path(".guard_partial_hash_preflight.txt").write_text(h, encoding="utf-8")
print("PASS — hash sauvegardé localement (non commité)")

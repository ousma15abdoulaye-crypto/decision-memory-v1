"""Calcule le GUARD hash selon la méthode exacte du test (pour diagnostic)."""
import ast
import hashlib
import pathlib
import re

service_path = pathlib.Path("src/couche_a/pipeline/service.py")
src = service_path.read_text(encoding="utf-8")

tree = ast.parse(src)
lines = src.splitlines()
func_src = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "run_pipeline_a_partial":
        func_src = "\n".join(lines[node.lineno - 1 : node.end_lineno])
        print(f"Fonction extraite : lignes {node.lineno}-{node.end_lineno}")
        break

if func_src is None:
    raise SystemExit("STOP — run_pipeline_a_partial introuvable")


def _normalize(source: str) -> str:
    source = re.sub(r"#[^\n]*", "", source)
    source = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
    source = re.sub(r"'''.*?'''", "", source, flags=re.DOTALL)
    ls = [ln.rstrip() for ln in source.splitlines() if ln.strip()]
    return "\n".join(ls)


normalized = _normalize(func_src)
h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
print(f"Hash (méthode test) : {h}")
print()
print("--- Début normalized (500 chars) ---")
print(normalized[:500])

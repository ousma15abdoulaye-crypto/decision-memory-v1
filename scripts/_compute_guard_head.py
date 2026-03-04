"""Calcule le GUARD hash de run_pipeline_a_partial sur HEAD (committé)."""
import ast
import hashlib
import pathlib
import re
import subprocess

result = subprocess.run(
    ["git", "show", "HEAD:src/couche_a/pipeline/service.py"],
    capture_output=True, text=True, encoding="utf-8"
)
src = result.stdout

tree = ast.parse(src)
lines = src.splitlines()
func_src = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "run_pipeline_a_partial":
        func_src = "\n".join(lines[node.lineno - 1 : node.end_lineno])
        print(f"HEAD: lignes {node.lineno}-{node.end_lineno}")
        break

if func_src is None:
    raise SystemExit("STOP — run_pipeline_a_partial introuvable dans HEAD")


def _normalize(source: str) -> str:
    source = re.sub(r"#[^\n]*", "", source)
    source = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
    source = re.sub(r"'''.*?'''", "", source, flags=re.DOTALL)
    ls = [ln.rstrip() for ln in source.splitlines() if ln.strip()]
    return "\n".join(ls)


normalized = _normalize(func_src)
h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
print(f"Hash HEAD  : {h}")

# Compare avec working tree
src_wt = pathlib.Path("src/couche_a/pipeline/service.py").read_text(encoding="utf-8")
tree_wt = ast.parse(src_wt)
lines_wt = src_wt.splitlines()
for node in ast.walk(tree_wt):
    if isinstance(node, ast.FunctionDef) and node.name == "run_pipeline_a_partial":
        func_src_wt = "\n".join(lines_wt[node.lineno - 1 : node.end_lineno])
        print(f"WT : lignes {node.lineno}-{node.end_lineno}")
        break

normalized_wt = _normalize(func_src_wt)
h_wt = hashlib.sha256(normalized_wt.encode("utf-8")).hexdigest()
print(f"Hash WT    : {h_wt}")
print()
if h == h_wt:
    print("IDENTIQUES — la fonction n'a pas changé entre HEAD et working tree")
else:
    print("DIVERGENTS — la fonction a changé !")
    # Diff
    head_lines = normalized.splitlines()
    wt_lines = normalized_wt.splitlines()
    for i, (a, b) in enumerate(zip(head_lines, wt_lines)):
        if a != b:
            print(f"  ligne {i+1} HEAD: {a!r}")
            print(f"  ligne {i+1} WT  : {b!r}")
    if len(head_lines) != len(wt_lines):
        print(f"  Nb lignes HEAD={len(head_lines)} WT={len(wt_lines)}")

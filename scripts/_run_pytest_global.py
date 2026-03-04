"""Run pytest global et écrit résultat dans pytest_global_result.txt."""
import subprocess, sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "--tb=short", "-q", "--no-header"],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
    cwd=r"C:\Users\abdoulaye.ousmane\decision-memory-v1"
)
output = result.stdout + result.stderr
lines = output.splitlines()
tail = "\n".join(lines[-20:])

with open("pytest_global_result.txt", "w", encoding="utf-8") as f:
    f.write(tail)
    f.write(f"\n=== returncode: {result.returncode} ===\n")

safe = tail.encode("ascii", errors="replace").decode("ascii")
print(safe)
print(f"=== returncode: {result.returncode} ===")

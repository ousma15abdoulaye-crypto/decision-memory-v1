"""Run pytest tests/db_integrity/test_m5_fix_market_signals.py et capture output."""
import subprocess, sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]

result = subprocess.run(
    [sys.executable, "-m", "pytest",
     "tests/db_integrity/test_m5_fix_market_signals.py",
     "--tb=short", "-v", "--no-header"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=REPO_ROOT
)
output = result.stdout + result.stderr
safe = output.encode("ascii", errors="replace").decode("ascii")
print(safe)
print(f"=== returncode: {result.returncode} ===")

"""scripts/run_tests_final.py"""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).parent.parent

r2 = subprocess.run(
    [sys.executable, "-m", "pytest",
     "--tb=line", "-q", "--no-header"],
    cwd=root
)
print(f"\n=== GLOBAL : exit {r2.returncode} ===\n")
sys.exit(r2.returncode)

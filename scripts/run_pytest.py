"""
scripts/run_pytest.py
Exécute pytest en foreground et capture l'output.
Contournement PowerShell Windows (Piège-07 DMS).
Usage : python scripts/run_pytest.py
"""
import subprocess
import sys
from pathlib import Path

result = subprocess.run(
    [
        sys.executable, "-m", "pytest",
        "--tb=short",
        "-q",
        "--no-header",
    ],
    cwd=Path(__file__).parent.parent,
    capture_output=False,   # output direct dans le terminal
    text=True,
)

sys.exit(result.returncode)

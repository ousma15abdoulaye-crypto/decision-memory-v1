"""Lance pytest et écrit la sortie dans pytest_result.txt."""
import subprocess
import sys
import os

env = os.environ.copy()
env["DATABASE_URL"] = "postgresql+psycopg://dms:dms123@localhost:5432/dms"

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "--tb=short", "-q", "--no-header"],
    capture_output=True,
    text=True,
    env=env,
    cwd=root,
)

output = result.stdout + result.stderr
out_path = os.path.join(root, "pytest_result.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(output)

tail = output[-4000:] if len(output) > 4000 else output
print(tail)
print(f"\nEXIT CODE: {result.returncode}")
sys.exit(result.returncode)

"""P3.2 ÉTAPE C — Delete 082 parasite and verify single head"""

import sys
import subprocess
from pathlib import Path

repo_root = Path(__file__).parent.parent
file_082 = repo_root / "alembic" / "versions" / "082_p32_dao_criteria_scoring_schema.py"

print("=" * 70)
print("P3.2 ÉTAPE C — SUPPRESSION 082 PARASITE")
print("=" * 70)
print()

# Check if exists
print("[1] Verification existence 082...")
if not file_082.exists():
    print("⛔ ERROR: 082_p32_dao_criteria_scoring_schema.py not found")
    print(f"   Path: {file_082}")
    sys.exit(1)

print(f"✅ Found: {file_082.name}")
print()

# Delete
print("[2] Deletion 082...")
try:
    file_082.unlink()
    print("✅ Deleted successfully")
except Exception as e:
    print(f"⛔ ERROR: {e}")
    sys.exit(1)

print()

# Verify deleted
print("[3] Verification deletion...")
if file_082.exists():
    print("⛔ ERROR: File still exists after deletion")
    sys.exit(1)

print("✅ File deleted confirmed")
print()

# Verify alembic heads
print("=" * 70)
print("[4] POST-CHECK: alembic heads")
print("=" * 70)
print()

result = subprocess.run(
    ["alembic", "heads"], cwd=repo_root, capture_output=True, text=True
)

print("STDOUT:")
print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)

heads_lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
n_heads = len(heads_lines)

print()
print(f"NUMBER OF HEADS: {n_heads}")

if n_heads != 1:
    print(f"⛔ ERROR: Expected 1 head, found {n_heads}")
    sys.exit(1)

print("✅ SINGLE HEAD CONFIRMED")
print()

# Verify alembic current
print("=" * 70)
print("[5] POST-CHECK: alembic current")
print("=" * 70)
print()

result = subprocess.run(
    ["alembic", "current"], cwd=repo_root, capture_output=True, text=True
)

print("STDOUT:")
print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)

print()
print("=" * 70)
print("ÉTAPE C COMPLETE — SINGLE HEAD RESTORED")
print("=" * 70)

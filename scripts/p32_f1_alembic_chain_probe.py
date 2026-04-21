"""P3.2 ACTION F1 — Alembic chain probe

Détermine :
1. Current head (alembic current)
2. Last migration number in versions/
3. Exact down_revision for migration 101
"""

import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
versions_dir = repo_root / "alembic" / "versions"

print("=" * 60)
print("P3.2 ACTION F1 — ALEMBIC CHAIN PROBE")
print("=" * 60)

# 1. Current head
print("\n[1] Current Alembic head:")
try:
    result = subprocess.run(
        ["alembic", "current"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode == 0:
        print(result.stdout.strip() or "(no output - possibly no migrations applied)")
        current_head = result.stdout.strip()
    else:
        print(f"ERROR: {result.stderr}")
        current_head = None
except Exception as e:
    print(f"ERROR: {e}")
    current_head = None

# 2. Last migration in versions/
print("\n[2] Last 10 migrations in alembic/versions/:")
migrations = []
for f in versions_dir.glob("[0-9]*.py"):
    try:
        num = int(f.stem.split("_")[0])
        migrations.append((num, f.name, f.stem))
    except (ValueError, IndexError):
        continue

migrations.sort()

if not migrations:
    print("ERROR: No migrations found")
    sys.exit(1)

for num, name, stem in migrations[-10:]:
    print(f"  {num:03d} — {name}")

last_num, last_name, last_stem = migrations[-1]
print(f"\n[3] Last migration:")
print(f"  Number: {last_num:03d}")
print(f"  File: {last_name}")
print(f"  Revision ID (stem): {last_stem}")

# 3. Read revision ID from last migration file
last_file = versions_dir / last_name
print(f"\n[4] Reading revision ID from {last_name}:")
try:
    with open(last_file, "r", encoding="utf-8") as f:
        content = f.read()
        for line in content.split("\n"):
            if line.strip().startswith("revision = "):
                revision_line = line.strip()
                print(f"  {revision_line}")
                # Extract revision ID
                revision_id = revision_line.split("=")[1].strip().strip("'\"")
                break
        else:
            print("  ERROR: No 'revision = ...' line found")
            revision_id = None
except Exception as e:
    print(f"  ERROR: {e}")
    revision_id = None

# 4. Recommendation for migration 101
print("\n" + "=" * 60)
print("RECOMMENDATION FOR MIGRATION 101")
print("=" * 60)
next_num = last_num + 1
print(f"\nNext migration number: {next_num:03d}")
print(f"File name: {next_num:03d}_p32_dao_criteria_scoring_schema.py")

if revision_id:
    print(f"\nSet in migration 101:")
    print(f"  down_revision = '{revision_id}'")
else:
    print("\n⚠️  Could not determine revision ID from last migration")
    print("   Manual check required")

print("\n" + "=" * 60)
print("ACTION F1 COMPLETE")
print("=" * 60)

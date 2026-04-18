"""P3.2 — Check last migration number in alembic/versions/"""
import os
from pathlib import Path

versions_dir = Path(__file__).parent.parent / "alembic" / "versions"

# Get all .py files starting with digits
migrations = []
for f in versions_dir.glob("[0-9]*.py"):
    try:
        num = int(f.stem.split("_")[0])
        migrations.append((num, f.name))
    except (ValueError, IndexError):
        continue

migrations.sort()

print("Last 10 migrations:")
for num, name in migrations[-10:]:
    print(f"  {num:03d} — {name}")

if migrations:
    last_num = migrations[-1][0]
    next_num = last_num + 1
    print(f"\nLast migration: {last_num:03d}")
    print(f"Next migration: {next_num:03d}_p32_dao_criteria_scoring_schema.py")
else:
    print("\nNo migrations found")

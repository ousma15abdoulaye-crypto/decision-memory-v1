"""P3.2 ÉTAPE A — Probe complet chaîne Alembic"""
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
versions_dir = repo_root / "alembic" / "versions"

print("=" * 70)
print("P3.2 ÉTAPE A — PROBE ALEMBIC HEADS")
print("=" * 70)
print()

# ===========================================================================
# 1. alembic heads
# ===========================================================================
print("=" * 70)
print("[1] alembic heads")
print("=" * 70)
print()

result = subprocess.run(
    ["alembic", "heads"],
    cwd=repo_root,
    capture_output=True,
    text=True
)

print("STDOUT:")
print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)
print(f"EXIT CODE: {result.returncode}")
print()

heads_output = result.stdout.strip()
heads_lines = [line for line in heads_output.split('\n') if line.strip()]
n_heads = len(heads_lines)

print(f"NUMBER OF HEADS: {n_heads}")
print()

# ===========================================================================
# 2. alembic current
# ===========================================================================
print("=" * 70)
print("[2] alembic current")
print("=" * 70)
print()

result = subprocess.run(
    ["alembic", "current"],
    cwd=repo_root,
    capture_output=True,
    text=True
)

print("STDOUT:")
print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)
print(f"EXIT CODE: {result.returncode}")
print()

# ===========================================================================
# 3. Liste tous fichiers migrations
# ===========================================================================
print("=" * 70)
print("[3] Liste fichiers alembic/versions/*.py")
print("=" * 70)
print()

migration_files = sorted([f for f in versions_dir.glob("*.py") if f.stem != "__init__"])
print(f"TOTAL: {len(migration_files)} fichiers\n")

for f in migration_files:
    print(f"  {f.name}")

print()

# ===========================================================================
# 4. Extraction revision + down_revision
# ===========================================================================
print("=" * 70)
print("[4] Extraction revision + down_revision (tous fichiers)")
print("=" * 70)
print()

migrations = []

for f in migration_files:
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            content = fh.read()

        revision = None
        down_revision = None

        for line in content.split('\n'):
            line_stripped = line.strip()
            if line_stripped.startswith('revision = '):
                revision = line_stripped.split('=', 1)[1].strip().strip('"\'')
            elif line_stripped.startswith('down_revision = '):
                down_revision = line_stripped.split('=', 1)[1].strip().strip('"\'')
                # Remove comments
                if '#' in down_revision:
                    down_revision = down_revision.split('#')[0].strip().strip('"\'')

        migrations.append({
            'file': f.name,
            'revision': revision,
            'down_revision': down_revision
        })

    except Exception as e:
        print(f"ERROR reading {f.name}: {e}")
        migrations.append({
            'file': f.name,
            'revision': '???',
            'down_revision': '???'
        })

# Print table
print(f"{'File':<50s} | {'revision':<40s} | {'down_revision':<40s}")
print("-" * 135)

for m in migrations:
    print(f"{m['file']:<50s} | {m['revision']:<40s} | {m['down_revision']:<40s}")

print()

# ===========================================================================
# 5. Identification heads concurrents
# ===========================================================================
print("=" * 70)
print("[5] Identification heads concurrents")
print("=" * 70)
print()

# Build graph: revision -> file
rev_to_file = {m['revision']: m['file'] for m in migrations if m['revision']}

# Find migrations that are NOT down_revision of anyone (= heads)
all_revisions = set(m['revision'] for m in migrations if m['revision'])
all_down_revisions = set(m['down_revision'] for m in migrations if m['down_revision'] and m['down_revision'] != 'None')

potential_heads = all_revisions - all_down_revisions

print(f"Potential heads (not referenced as down_revision): {len(potential_heads)}")
for rev in sorted(potential_heads):
    file = rev_to_file.get(rev, '???')
    print(f"  {rev:<40s} <- {file}")

print()

# Check if 082 exists (created by mistake earlier)
file_082 = versions_dir / "082_p32_dao_criteria_scoring_schema.py"
if file_082.exists():
    print("⚠️  WARNING: 082_p32_dao_criteria_scoring_schema.py exists (created by mistake)")
    print("   This file should be deleted/ignored")
    print()

print("=" * 70)
print("PROBE COMPLETE")
print("=" * 70)

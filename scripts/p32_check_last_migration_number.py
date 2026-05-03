"""P3.2 — Check last migration number in alembic/versions/

Scans ALL migration files (including non-numeric IDs like e7df16ec18ee_*.py)
and builds the true Alembic graph to identify real heads.
Handles tuple down_revision values produced by merge migrations.
"""

import ast
import re
from pathlib import Path

versions_dir = Path(__file__).parent.parent / "alembic" / "versions"


def _parse_revision_value(raw: str):
    """Return a set of revision strings from a raw assignment value.

    Handles:
    - plain string:  'abc123'
    - tuple literal: ('rev_a', 'rev_b')
    - None literal
    """
    raw = raw.strip()
    if raw in ("None", ""):
        return set()
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        # Fallback: strip quotes around a bare string
        return {raw.strip("'\"")}
    if isinstance(value, (list, tuple)):
        return {str(v) for v in value}
    return {str(value)}


# Scan ALL *.py files except __init__.py
all_files = sorted(f for f in versions_dir.glob("*.py") if f.stem != "__init__")

migrations = []
for f in all_files:
    try:
        content = f.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"WARNING: cannot read {f.name}: {exc}")
        continue

    revision = None
    down_revision_raw = None

    for line in content.splitlines():
        stripped = line.strip()
        if re.match(r"^revision\s*=\s*", stripped) and revision is None:
            revision = stripped.split("=", 1)[1].strip().strip("'\"")
        elif re.match(r"^down_revision\s*=\s*", stripped) and down_revision_raw is None:
            down_revision_raw = stripped.split("=", 1)[1].split("#")[0].strip()

    if revision is None:
        continue  # not a migration file

    down_revisions = _parse_revision_value(down_revision_raw or "None")

    # Detect numeric prefix for naming purposes
    numeric_prefix = None
    try:
        numeric_prefix = int(f.stem.split("_")[0])
    except (ValueError, IndexError):
        pass

    migrations.append(
        {
            "file": f.name,
            "revision": revision,
            "down_revisions": down_revisions,
            "numeric_prefix": numeric_prefix,
        }
    )

# Build graph: collect all down_revisions referenced by any migration
all_down_revisions: set = set()
for m in migrations:
    all_down_revisions.update(m["down_revisions"])

# True Alembic heads = revisions not referenced as someone else's down_revision
all_revisions = {m["revision"] for m in migrations}
heads = all_revisions - all_down_revisions

rev_to_file = {m["revision"]: m["file"] for m in migrations}

# Numeric migrations sorted by prefix (for "last migration number" display)
numeric_migrations = sorted(
    (m for m in migrations if m["numeric_prefix"] is not None),
    key=lambda m: m["numeric_prefix"],
)

print("=" * 70)
print("P3.2 — Migration inventory (ALL files, including non-numeric IDs)")
print("=" * 70)

print(f"\nTotal migration files scanned: {len(migrations)}")
print(f"  — numeric prefix : {len(numeric_migrations)}")
print(f"  — non-numeric    : {len(migrations) - len(numeric_migrations)}")

print("\nLast 10 numeric migrations:")
for m in numeric_migrations[-10:]:
    print(f"  {m['numeric_prefix']:03d} — {m['file']}")

print(f"\nTrue Alembic heads (not referenced as down_revision): {len(heads)}")
for rev in sorted(heads):
    print(f"  {rev:<50s} ← {rev_to_file.get(rev, '???')}")

if numeric_migrations:
    last_num = numeric_migrations[-1]["numeric_prefix"]
    next_num = last_num + 1
    print(f"\nLast numeric migration : {last_num:03d}")
    print(f"Suggested next number  : {next_num:03d}")
    print(
        "NOTE: set down_revision to the TRUE head(s) above, "
        "not necessarily to the last numeric file."
    )
else:
    print("\nNo numeric migrations found")

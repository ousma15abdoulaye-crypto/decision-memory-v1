"""List migrations in alembic/versions/"""
from pathlib import Path

versions_dir = Path(__file__).parent.parent / "alembic" / "versions"

migrations = []
for f in versions_dir.glob("*.py"):
    if f.stem == "__init__":
        continue
    try:
        # Try to extract number from filename
        parts = f.stem.split("_")
        if parts[0].isdigit():
            num = int(parts[0])
            migrations.append((num, f.name))
    except (ValueError, IndexError):
        pass

migrations.sort()

print("All migrations:")
for num, name in migrations:
    print(f"{num:03d} {name}")

if migrations:
    last_num, last_name = migrations[-1]
    print(f"\nLast: {last_num:03d} {last_name}")
    print(f"Next: {last_num + 1:03d}_p32_dao_criteria_scoring_schema.py")

    # Read last migration to get revision ID
    last_file = versions_dir / last_name
    with open(last_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith("revision = "):
                print(f"\n{line.strip()}")
                rev_id = line.split("=")[1].strip().strip("'\"")
                print(f"down_revision for 101: '{rev_id}'")
                break

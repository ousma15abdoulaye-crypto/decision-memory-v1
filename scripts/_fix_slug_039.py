"""
Correction: revision slug trop long (36 chars > VARCHAR(32)).
Utilise 039_created_at_timestamptz (26 chars) -- meme semantique, respecte la limite.
"""
import psycopg
import os

OLD_SLUG = "039_hardening_created_at_timestamptz"  # 36 chars -- trop long
NEW_SLUG = "039_created_at_timestamptz"              # 26 chars -- OK

# 1. Patch le fichier migration
mig = "alembic/versions/039_hardening_created_at_timestamptz.py"
txt = open(mig, encoding="utf-8").read()
txt = txt.replace(f'revision = "{OLD_SLUG}"', f'revision = "{NEW_SLUG}"')
# Mettre a jour aussi le docstring
txt = txt.replace(
    f"Revision ID: {OLD_SLUG}",
    f"Revision ID: {NEW_SLUG}"
)
open(mig, "w", encoding="utf-8").write(txt)
print(f"[1] {mig}: revision -> {NEW_SLUG}")

# Verif
for line in open(mig, encoding="utf-8"):
    if "revision" in line.lower() and "down" not in line and "branch" not in line and "depends" not in line:
        print(f"    {line.rstrip()}")

# 2. Mettre a jour alembic_version en DB locale
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("[2] DATABASE_URL absente -- skip UPDATE alembic_version")
else:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE alembic_version SET version_num = %s WHERE version_num IN (%s, %s)",
                (NEW_SLUG, OLD_SLUG, "039")
            )
            print(f"[2] alembic_version updated: {cur.rowcount} row(s)")
        conn.commit()

"""
Correctif PIÈGE-4 : état bloqué après downgrade m5_pre_vendors_consolidation.

Situation :
  - alembic current = m4_patch_a_fix
  - vendor_identities existe (renommée depuis vendors par le downgrade)
  - vendors legacy absente (non recréée par le downgrade)
  - m5_pre_vendors_consolidation.upgrade() bloque sur Garde 2 (vendors legacy absente)

Correctif :
  1. Créer une table vendors legacy minimale (id INTEGER, 4 colonnes de 005_add_couche_b)
  2. alembic upgrade head peut alors exécuter m5_pre_vendors_consolidation
     qui droppera vendors legacy et renommera vendor_identities → vendors
  3. Puis m5_fix_market_signals_vendor_type s'applique
"""

import os
import subprocess

from dotenv import load_dotenv

load_dotenv()
import psycopg
import psycopg.rows

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row)
conn.autocommit = True

print("=== ÉTAT ACTUEL ===")
with conn.cursor() as cur:
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name IN ('vendors','vendor_identities','market_signals') "
        "ORDER BY table_name"
    )
    for row in cur.fetchall():
        print("  TABLE:", row["table_name"])

# Vérifier si vendors legacy existe déjà
with conn.cursor() as cur:
    cur.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='vendors'"
    )
    vendors_exists = cur.fetchone() is not None

if vendors_exists:
    print("vendors legacy existe déjà — aucune action requise")
else:
    print("\n=== CRÉATION vendors legacy minimale ===")
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vendors (
                id          SERIAL PRIMARY KEY,
                name        TEXT NOT NULL,
                region_code TEXT,
                created_at  TEXT DEFAULT NOW()::TEXT
            )
        """)
    print("  vendors legacy créée (0 lignes)")

conn.close()

print("\n=== ALEMBIC UPGRADE HEAD ===")
result = subprocess.run(
    ["alembic", "upgrade", "head"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)
stdout = result.stdout.encode("ascii", errors="replace").decode("ascii")
stderr = result.stderr.encode("ascii", errors="replace").decode("ascii")
print("STDOUT:", stdout[-3000:] if len(stdout) > 3000 else stdout)
print("STDERR:", stderr[-3000:] if len(stderr) > 3000 else stderr)
print("EXIT CODE:", result.returncode)

#!/usr/bin/env python3
"""Probe final M7.3 - etat complet post-migration."""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row

url = os.environ.get("DATABASE_URL", "").replace(
    "postgresql+psycopg://", "postgresql://"
)
if not url:
    sys.exit("DATABASE_URL manquante")

conn = psycopg.connect(url, row_factory=dict_row)

# Tables M7.3 presentes
tables = [
    "dict_price_references",
    "dict_uom_conversions",
    "dgmp_thresholds",
    "dict_item_suppliers",
]
for t in tables:
    r = conn.execute(f"SELECT COUNT(*) AS n FROM couche_b.{t}").fetchone()
    print(f"{t}: {r['n']} lignes")

# Colonnes ajoutees
cols = conn.execute(
    """
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = %s AND table_name = %s
    AND column_name IN (
        %s,%s,%s,%s,%s,%s,%s,%s,%s
    )
    ORDER BY column_name
""",
    (
        "couche_b",
        "procurement_dict_items",
        "item_type",
        "default_uom",
        "default_currency",
        "unspsc_code",
        "classification_confidence",
        "classification_source",
        "needs_review",
        "quality_score",
        "last_hash",
    ),
).fetchall()
print(f"Colonnes M7.3 : {len(cols)}/9")
for c in cols:
    print(f"  {c['column_name']}: {c['data_type']}")

# DGMP seed
r = conn.execute("SELECT COUNT(*) AS n FROM couche_b.dgmp_thresholds").fetchone()
print(f"DGMP thresholds seeded: {r['n']} lignes")

# UOM seed
r = conn.execute("SELECT COUNT(*) AS n FROM couche_b.dict_uom_conversions").fetchone()
print(f"UOM conversions seeded: {r['n']} lignes")

# Audit log DICT_ITEM
r = conn.execute(
    "SELECT COUNT(*) AS n FROM public.audit_log WHERE entity = %s", ("DICT_ITEM",)
).fetchone()
print(f"audit_log DICT_ITEM entries: {r['n']}")

# Alembic
r = conn.execute("SELECT version_num FROM alembic_version").fetchone()
print(f"alembic_version: {r['version_num']}")

conn.close()

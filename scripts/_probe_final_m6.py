"""Probe final M6 · dict par famille · seed · matcher · vues."""
from dotenv import load_dotenv
load_dotenv()
load_dotenv(".env.local")
import psycopg
import os
from psycopg.rows import dict_row

url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(url, row_factory=dict_row) as conn:
    print("=== DICT ITEMS PAR FAMILLE ===")
    rows = conn.execute(
        """
        SELECT
            f.label_fr,
            f.criticite,
            COUNT(i.item_id) AS nb_items
        FROM couche_b.procurement_dict_families f
        LEFT JOIN couche_b.procurement_dict_items i
            ON i.family_id = f.family_id
        GROUP BY f.family_id, f.label_fr, f.criticite
        ORDER BY nb_items DESC
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== ITEMS SEED INTACTS ===")
    rows = conn.execute(
        """
        SELECT item_id, confidence_score, human_validated
        FROM couche_b.procurement_dict_items
        WHERE human_validated = TRUE
        LIMIT 5
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== MATCHER TEST ===")
    rows = conn.execute(
        """
        SELECT
            i.item_id,
            i.label_fr,
            a.normalized_alias,
            a.source
        FROM couche_b.procurement_dict_aliases a
        JOIN couche_b.procurement_dict_items i
            ON i.item_id = a.item_id
        WHERE a.normalized_alias IN (
            'gasoil', 'ciment_cpa_42.5',
            'fer_ha_10mm'
        )
        ORDER BY a.normalized_alias
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== VUES PUBLIC ===")
    for v in ["dict_items", "dict_aliases", "dict_families", "dict_units"]:
        r = conn.execute(
            f"SELECT COUNT(*) AS n FROM public.{v}"
        ).fetchone()
        print(f"  {v} : {r['n']} lignes")

    print("=== ALEMBIC ===")
    r = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    print(f"  head : {r['version_num']}")

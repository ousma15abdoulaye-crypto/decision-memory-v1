"""Probe STOP complementaire · contenu réel + FK · Tech Lead mandat."""
from dotenv import load_dotenv
load_dotenv()
load_dotenv(".env.local")
import psycopg
import os
from psycopg.rows import dict_row

url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
if not url:
    print("DATABASE_URL non definie")
    exit(1)

with psycopg.connect(url, row_factory=dict_row) as conn:
    print("=== procurement_dict_items (echantillon) ===")
    rows = conn.execute(
        """
        SELECT * FROM couche_b.procurement_dict_items
        LIMIT 10
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== procurement_dict_aliases (echantillon) ===")
    rows = conn.execute(
        """
        SELECT * FROM couche_b.procurement_dict_aliases
        LIMIT 10
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== procurement_dict_families ===")
    rows = conn.execute(
        """
        SELECT * FROM couche_b.procurement_dict_families
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== couche_b.procurement_dict_units ===")
    rows = conn.execute(
        """
        SELECT * FROM couche_b.procurement_dict_units
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== FK vers public.dict_items ===")
    rows = conn.execute(
        """
        SELECT
            tc.table_schema,
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON tc.constraint_name = ccu.constraint_name
        WHERE ccu.table_name IN (
            'dict_items', 'dict_aliases',
            'dict_families'
        )
        AND tc.constraint_type = 'FOREIGN KEY'
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== Alembic chain autour de 021 ===")
    rows = conn.execute(
        """
        SELECT indexname FROM pg_indexes
        WHERE tablename IN (
            'dict_items','dict_aliases',
            'dict_families'
        )
        ORDER BY indexname
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

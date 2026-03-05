"""Probe complet couche_b · structure + contraintes + index + vues."""
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
    print("=== COLONNES procurement_dict_items ===")
    rows = conn.execute(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'couche_b'
          AND table_name   = 'procurement_dict_items'
        ORDER BY ordinal_position
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== COLONNES procurement_dict_aliases ===")
    rows = conn.execute(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'couche_b'
          AND table_name   = 'procurement_dict_aliases'
        ORDER BY ordinal_position
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== CONTRAINTES couche_b dict ===")
    rows = conn.execute(
        """
        SELECT
            tc.table_name,
            tc.constraint_name,
            tc.constraint_type,
            kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_schema = 'couche_b'
          AND tc.table_name IN (
              'procurement_dict_items',
              'procurement_dict_aliases'
          )
        ORDER BY tc.table_name, tc.constraint_type
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== INDEX couche_b dict ===")
    rows = conn.execute(
        """
        SELECT schemaname, tablename, indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'couche_b'
          AND tablename IN (
              'procurement_dict_items',
              'procurement_dict_aliases',
              'procurement_dict_families',
              'procurement_dict_units'
          )
        ORDER BY tablename, indexname
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== VUES PUBLIC -> couche_b ===")
    rows = conn.execute(
        """
        SELECT table_name, view_definition
        FROM information_schema.views
        WHERE table_schema = 'public'
          AND table_name IN (
              'dict_items', 'dict_aliases',
              'dict_families', 'dict_units'
          )
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== ALEMBIC CURRENT ===")
    r = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    print(" ", r["version_num"])

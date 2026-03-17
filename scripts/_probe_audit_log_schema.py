#!/usr/bin/env python3
"""Probe audit_log schema reel · REGLE-08."""
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

URL = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
if not URL:
    sys.exit("DATABASE_URL manquante")

with psycopg.connect(URL, row_factory=dict_row) as conn:

    print("=== TABLES AUDIT/HASH EXISTANTES ===")
    rows = conn.execute("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_name ILIKE '%audit%'
           OR table_name ILIKE '%hash%'
           OR table_name ILIKE '%history%'
           OR table_name ILIKE '%chain%'
        ORDER BY table_schema, table_name
    """).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("\n=== COLONNES audit_log ===")
    rows = conn.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'audit_log'
        ORDER BY ordinal_position
    """).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("\n=== CONTRAINTES audit_log ===")
    rows = conn.execute("""
        SELECT constraint_name, constraint_type
        FROM information_schema.table_constraints
        WHERE table_schema = 'public' AND table_name = 'audit_log'
    """).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("\n=== INDEX audit_log ===")
    rows = conn.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = 'audit_log'
        ORDER BY indexname
    """).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("\n=== TRIGGERS EXISTANTS audit/hash ===")
    rows = conn.execute("""
        SELECT trigger_schema, trigger_name,
               event_object_table, action_timing,
               event_manipulation
        FROM information_schema.triggers
        WHERE trigger_name ILIKE '%audit%'
           OR trigger_name ILIKE '%hash%'
           OR trigger_name ILIKE '%history%'
        ORDER BY trigger_schema, trigger_name
    """).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("\n=== FONCTIONS AUDIT/HASH EXISTANTES ===")
    rows = conn.execute("""
        SELECT routine_schema, routine_name, routine_type
        FROM information_schema.routines
        WHERE routine_schema = 'public'
          AND (routine_name ILIKE '%audit%' OR routine_name ILIKE '%hash%')
        ORDER BY routine_name
    """).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("\n=== ECHANTILLON audit_log (5 lignes) ===")
    try:
        rows = conn.execute("SELECT * FROM public.audit_log LIMIT 5").fetchall()
        for r in rows:
            print(" ", dict(r))
        if not rows:
            print("  (vide)")
    except Exception as e:
        print(" ", e)

    print("\n=== ENTITY VALUES EXISTANTS dans audit_log ===")
    try:
        rows = conn.execute("""
            SELECT DISTINCT entity, COUNT(*) AS n
            FROM public.audit_log
            GROUP BY entity
            ORDER BY n DESC
        """).fetchall()
        for r in rows:
            print(" ", dict(r))
        if not rows:
            print("  (vide)")
    except Exception as e:
        print(" ", e)

    print("\n=== COUNT audit_log ===")
    try:
        r = conn.execute("SELECT COUNT(*) AS n FROM public.audit_log").fetchone()
        print("  n =", r["n"])
    except Exception as e:
        print(" ", e)

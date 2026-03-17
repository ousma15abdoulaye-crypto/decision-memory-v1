#!/usr/bin/env python3
"""PREUVE 1 + 2 — Identité DB + M7.2 prérequis."""
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

with psycopg.connect(URL, row_factory=dict_row) as c:
    # PREUVE 1
    r = c.execute("select current_database() db, inet_server_addr() host, inet_server_port() port").fetchone()
    a = c.execute("select version_num from alembic_version").fetchone()
    v = c.execute("select count(*) n from public.vendors").fetchone()
    print("--- PREUVE 1 ---")
    print(dict(r))
    print("alembic_version=", a["version_num"])
    print("public.vendors=", v["n"])

    # PREUVE 2
    t = c.execute("""
        select count(*) n from information_schema.tables
        where table_schema='couche_b' and table_name='taxo_l1_domains'
    """).fetchone()
    print("\n--- PREUVE 2 ---")
    print("alembic_version=", a["version_num"])
    print("couche_b.taxo_l1_domains exists=", t["n"])

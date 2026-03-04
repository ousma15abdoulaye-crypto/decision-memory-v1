"""PROBE M2B — Lecture seule. Vérifie l'état réel de la DB.

Usage :
  python scripts/probe_m2b.py                  # DB locale (.env)
  python scripts/probe_m2b.py <DATABASE_URL>   # DB Railway prod (URL publique)
"""

import os
import sys

from dotenv import load_dotenv

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("ERROR: psycopg non installé.")
    sys.exit(1)


def get_url() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    load_dotenv()
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("ERROR: DATABASE_URL non défini.")
        sys.exit(1)
    return url.replace("postgresql+psycopg://", "postgresql://")


def probe(url: str) -> None:
    db_label = "RAILWAY PROD" if "railway" in url.lower() or "rlwy" in url.lower() else "LOCAL DEV"
    print(f"\n{'='*60}")
    print(f"PROBE M2B — {db_label}")
    print(f"URL : {url[:50]}...")
    print(f"{'='*60}\n")

    with psycopg.connect(url, row_factory=dict_row, autocommit=True) as conn:
        with conn.cursor() as cur:

            # ─── PROBE 1 — users.created_at ───────────────────────────
            print("─── PROBE 1A : users.created_at column definition ───")
            cur.execute("""
                SELECT column_name, data_type, udt_name, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'created_at'
            """)
            for r in cur.fetchall():
                print(dict(r))

            print("\n─── PROBE 1B : sample rows created_at ───")
            cur.execute("""
                SELECT id, created_at, pg_typeof(created_at) AS pg_type
                FROM users ORDER BY id LIMIT 20
            """)
            for r in cur.fetchall():
                print(dict(r))

            print("\n─── PROBE 1C : total_users ───")
            cur.execute("SELECT COUNT(*) AS total_users FROM users")
            print(dict(cur.fetchone()))

            # ─── PROBE 2 — FK NOT VALID ────────────────────────────────
            print("\n─── PROBE 2A : NOT VALID constraints ───")
            cur.execute("""
                SELECT conname, contype, convalidated, conrelid::regclass AS table_name
                FROM pg_constraint
                WHERE convalidated = false
                ORDER BY conrelid::regclass::text, conname
            """)
            rows = cur.fetchall()
            if rows:
                for r in rows:
                    print(dict(r))
            else:
                print("AUCUNE CONTRAINTE NOT VALID")

            print("\n─── PROBE 2B : orphan_count pipeline_runs ───")
            cur.execute("""
                SELECT COUNT(*) AS orphan_count
                FROM pipeline_runs pr
                LEFT JOIN cases c ON c.id = pr.case_id
                WHERE pr.case_id IS NOT NULL AND c.id IS NULL
            """)
            print(dict(cur.fetchone()))

            print("\n─── PROBE 2C : total_pipeline_runs ───")
            cur.execute("SELECT COUNT(*) AS total_pipeline_runs FROM pipeline_runs")
            print(dict(cur.fetchone()))

            # ─── PROBE 3 — role_id column ─────────────────────────────
            print("\n─── PROBE 3 : users.role_id column ───")
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'role_id'
            """)
            rows = cur.fetchall()
            if rows:
                for r in rows:
                    print(dict(r))
            else:
                print("COLONNE role_id ABSENTE")

            # ─── PROBE 5 — Comptes smoke/debug ────────────────────────
            print("\n─── PROBE 5 : smoke/debug accounts ───")
            cur.execute("""
                SELECT id, username, email, created_at
                FROM users
                WHERE email ILIKE '%smoke%'
                   OR email ILIKE '%debug%'
                   OR username ILIKE 'smoke_%'
                   OR username ILIKE 'dbg_%'
                ORDER BY created_at DESC
            """)
            rows = cur.fetchall()
            if rows:
                for r in rows:
                    print(dict(r))
            else:
                print("AUCUN compte smoke/debug")

            print("\n─── ALL USERS (id + username + email) ───")
            cur.execute("SELECT id, username, email FROM users ORDER BY id")
            for r in cur.fetchall():
                print(dict(r))


if __name__ == "__main__":
    probe(get_url())

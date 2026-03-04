# scripts/_probe_m9_post.py  <- NE PAS COMMITTER
import os
import psycopg
from psycopg.rows import dict_row

with open(".env") as f:
    for line in f:
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            url = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

if url.startswith("postgresql+psycopg://"):
    url = url.replace("postgresql+psycopg://", "postgresql://", 1)

TABLES_EXPECTED = [
    "committees",
    "committee_members",
    "committee_decisions",
    "committee_events",
    "decision_snapshots",
]

FUNCTIONS_EXPECTED = [
    "enforce_committee_events_append_only",
    "enforce_decision_snapshots_append_only",
    "enforce_committee_lock",
    "enforce_committee_terminal_status",
]

TRIGGERS_EXPECTED = [
    "trg_committee_events_append_only",
    "trg_decision_snapshots_append_only",
    "trg_committee_members_lock",
    "trg_committee_decisions_lock",
    "trg_committees_terminal_status_lock",
]

with psycopg.connect(url, row_factory=dict_row) as conn:
    with conn.cursor() as cur:

        print("=== TABLES COMITE ===")
        for t in TABLES_EXPECTED:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name=%s) AS ok",
                (t,),
            )
            print(f"  {t:40s} : {cur.fetchone()['ok']}")

        print("\n=== FUNCTIONS (pg_proc) ===")
        for fn in FUNCTIONS_EXPECTED:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_proc p "
                "JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE n.nspname='public' AND p.proname=%s) AS ok",
                (fn,),
            )
            print(f"  {fn:45s} : {cur.fetchone()['ok']}")

        print("\n=== TRIGGERS ===")
        for trg in TRIGGERS_EXPECTED:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.triggers "
                "WHERE trigger_schema='public' AND trigger_name=%s) AS ok",
                (trg,),
            )
            print(f"  {trg:45s} : {cur.fetchone()['ok']}")

        print("\n=== ALEMBIC HEAD ===")
        cur.execute("SELECT version_num FROM alembic_version")
        for r in cur.fetchall():
            print(f"  {r['version_num']}")

        print("\n=== FK CROSS-TABLE ===")
        for t in TABLES_EXPECTED:
            cur.execute(
                "SELECT kcu.column_name, ccu.table_name AS foreign_table, "
                "ccu.column_name AS foreign_column "
                "FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "  ON tc.constraint_name=kcu.constraint_name "
                " AND tc.table_schema=kcu.table_schema "
                "JOIN information_schema.constraint_column_usage ccu "
                "  ON ccu.constraint_name=tc.constraint_name "
                " AND ccu.constraint_schema=tc.table_schema "
                "WHERE tc.constraint_type='FOREIGN KEY' "
                "  AND tc.table_schema='public' AND tc.table_name=%s",
                (t,),
            )
            for fk in cur.fetchall():
                print(f"  {t}.{fk['column_name']} -> {fk['foreign_table']}.{fk['foreign_column']}")

print("\nProbe M9 post-migration OK")

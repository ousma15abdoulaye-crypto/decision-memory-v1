"""ACTE 6 — Option A · DELETE case smoke + user smoke · IDs validés CTO.

Usage : python scripts/_acte6_option_a.py <RAILWAY_DB_URL>
IDs validés explicitement : case = c035e6fb-..., user = 10.
"""

import sys
import psycopg
from psycopg.rows import dict_row

if len(sys.argv) < 2:
    sys.exit("Usage: python scripts/_acte6_option_a.py <DATABASE_URL>")

url = sys.argv[1]
CASE_ID = "c035e6fb-f58a-4010-8ba9-cbf18d75b0ca"
USER_ID = 10

with psycopg.connect(url, row_factory=dict_row, autocommit=False) as conn:
    with conn.cursor() as cur:

        # Étape 1 — vérification avant opération
        cur.execute(
            """
            SELECT c.id AS case_id, c.title AS case_title,
                   c.owner_id, u.username AS owner_username, u.email AS owner_email
            FROM cases c
            JOIN users u ON u.id = c.owner_id
            WHERE c.id = %s
        """,
            (CASE_ID,),
        )
        row = cur.fetchone()
        print("ETAPE 1 - verification avant DELETE:")
        print(" ", dict(row) if row else "AUCUNE LIGNE")
        if not row or row["owner_username"] != "smoke_0b6609bc":
            print("STOP — owner_username inattendu · annulation")
            conn.rollback()
            sys.exit(1)

        # Étape 2 — total_cases avant
        cur.execute("SELECT COUNT(*) AS total_cases FROM cases")
        total = dict(cur.fetchone())
        print("\nETAPE 2 - total_cases avant DELETE:", total)
        if total["total_cases"] != 1:
            print("STOP — total_cases != 1 · annulation")
            conn.rollback()
            sys.exit(1)

        # Étape 3 — DELETE case
        cur.execute("DELETE FROM cases WHERE id = %s", (CASE_ID,))
        print(f"\nETAPE 3 - DELETE cases: {cur.rowcount} ligne(s)")
        conn.commit()

        # Étape 4 — confirmer case supprimée
        cur.execute("SELECT COUNT(*) AS total_cases FROM cases")
        print("ETAPE 4 - total_cases apres DELETE:", dict(cur.fetchone()))

        # Étape 5 — DELETE user
        cur.execute("DELETE FROM users WHERE id = %s", (USER_ID,))
        print(f"\nETAPE 5 - DELETE users: {cur.rowcount} ligne(s)")
        conn.commit()

        # Étape 6 — confirmer user supprimé
        cur.execute("SELECT COUNT(*) AS remaining FROM users WHERE id = %s", (USER_ID,))
        print("ETAPE 6 - remaining id=10:", dict(cur.fetchone()))

        # Étape 7 — zéro résidu smoke
        cur.execute("""
            SELECT id, username, email FROM users
            WHERE email ILIKE '%smoke%' OR email ILIKE '%debug%'
               OR username ILIKE 'smoke_%' OR username ILIKE 'dbg_%'
        """)
        rows = cur.fetchall()
        print(
            "\nETAPE 7a - smoke/debug restants:",
            [dict(r) for r in rows] if rows else "0 rows",
        )

        cur.execute("SELECT COUNT(*) AS total_users FROM users")
        print("ETAPE 7b - total_users:", dict(cur.fetchone()))

        cur.execute("SELECT COUNT(*) AS total_cases FROM cases")
        print("ETAPE 7c - total_cases:", dict(cur.fetchone()))

        # Étape 8 — FK NOT VALID résiduelles
        cur.execute("""
            SELECT conname, contype, convalidated, conrelid::regclass AS table_name
            FROM pg_constraint
            WHERE contype = 'f' AND convalidated = false
            ORDER BY conrelid::regclass::text
        """)
        fk_rows = cur.fetchall()
        print(
            "\nETAPE 8 - FK NOT VALID:",
            [dict(r) for r in fk_rows] if fk_rows else "0 rows",
        )

del url

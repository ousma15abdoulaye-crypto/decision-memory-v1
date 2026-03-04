"""ACTE 6 — DELETE compte smoke prod · ID 10 · validé humainement.

Usage : python scripts/_acte6_delete_smoke.py <RAILWAY_DB_URL>
URL non stockée. ID validé explicitement par CTO.
"""
import sys
import psycopg
from psycopg.rows import dict_row

if len(sys.argv) < 2:
    print("Usage: python scripts/_acte6_delete_smoke.py <DATABASE_URL>")
    sys.exit(1)

url = sys.argv[1]
VALIDATED_ID = 10

with psycopg.connect(url, row_factory=dict_row, autocommit=False) as conn:
    with conn.cursor() as cur:

        # Étape 1 — Vérification avant DELETE
        cur.execute(
            "SELECT id, username, email, created_at FROM users WHERE id = %s",
            (VALIDATED_ID,),
        )
        row = cur.fetchone()
        print("ETAPE 1 - avant DELETE:")
        print(" ", dict(row) if row else "AUCUNE LIGNE — id introuvable")

        if not row:
            print("STOP — id non trouvé · DELETE annulé")
            conn.rollback()
            sys.exit(1)

        # Étape 2 — DELETE sur ID explicite
        cur.execute("DELETE FROM users WHERE id = %s", (VALIDATED_ID,))
        deleted = cur.rowcount
        conn.commit()
        print(f"\nETAPE 2 - DELETE: {deleted} ligne(s) supprimee(s)")

        # Étape 3 — Confirmation post-DELETE
        cur.execute(
            "SELECT COUNT(*) AS remaining FROM users WHERE id = %s",
            (VALIDATED_ID,),
        )
        print("ETAPE 3 - remaining:", dict(cur.fetchone()))

        # Étape 4 — Zéro autre compte smoke/debug
        cur.execute("""
            SELECT id, username, email
            FROM users
            WHERE email ILIKE '%smoke%'
               OR email ILIKE '%debug%'
               OR username ILIKE 'smoke_%'
               OR username ILIKE 'dbg_%'
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        if rows:
            print("\nETAPE 4 - comptes smoke/debug restants:")
            for r in rows:
                print(" ", dict(r))
        else:
            print("\nETAPE 4 - 0 rows — aucun compte smoke/debug restant")

        # État final users
        cur.execute("SELECT id, username, email FROM users ORDER BY id")
        print("\nALL USERS post-DELETE:")
        for r in cur.fetchall():
            print(" ", dict(r))

del url

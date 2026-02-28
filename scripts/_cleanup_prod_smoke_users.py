"""Nettoyage comptes smoke/test/dbg créés en prod pendant M2.

Usage :
  python scripts/_cleanup_prod_smoke_users.py <DATABASE_URL_PUBLIC>

  DATABASE_URL_PUBLIC : URL publique Railway PostgreSQL
  (Railway UI → Postgres service → Connect → Public URL)

Ce script :
  1. Affiche les comptes qui seront supprimés (preview)
  2. Demande confirmation
  3. Exécute le DELETE
  4. Confirme le nombre de lignes supprimées
"""

import sys

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("ERROR: psycopg non installé. Lancer: pip install psycopg[binary]")
    sys.exit(1)

DELETE_SQL = """
DELETE FROM users
WHERE email LIKE '%@smoke-test.com'
   OR email LIKE '%@test.com'
   OR username LIKE 'smoke_%'
   OR username LIKE 'dbg_%'
   OR username LIKE 'test_%'
"""

SELECT_SQL = """
SELECT id, email, username, created_at
FROM users
WHERE email LIKE '%@smoke-test.com'
   OR email LIKE '%@test.com'
   OR username LIKE 'smoke_%'
   OR username LIKE 'dbg_%'
   OR username LIKE 'test_%'
ORDER BY id
"""

COUNT_SQL = "SELECT COUNT(*) AS n FROM users"


def main(db_url: str) -> None:
    url = db_url.replace("postgresql+psycopg://", "postgresql://")

    print(f"\n[cleanup] Connexion à : {url[:40]}...\n")

    with psycopg.connect(url, row_factory=dict_row, autocommit=False) as conn:
        with conn.cursor() as cur:

            # 1. Preview
            cur.execute(SELECT_SQL)
            rows = cur.fetchall()
            if not rows:
                print("[cleanup] Aucun compte smoke/test/dbg trouvé. Rien à supprimer.")
                return

            print(f"[cleanup] {len(rows)} compte(s) à supprimer :\n")
            for r in rows:
                print(f"  id={r['id']:>3}  username={r['username']:<30}  email={r['email']}")

            # 2. Confirmation
            print()
            ans = input("Confirmer la suppression ? (oui/non) : ").strip().lower()
            if ans not in ("oui", "o", "yes", "y"):
                print("[cleanup] Suppression annulée.")
                conn.rollback()
                return

            # 3. DELETE
            cur.execute(DELETE_SQL)
            deleted = cur.rowcount
            conn.commit()

            # 4. Confirmation
            cur.execute(COUNT_SQL)
            total = cur.fetchone()["n"]
            print(f"\n[cleanup] DELETE {deleted} — OK")
            print(f"[cleanup] Comptes restants en DB : {total} (doit contenir admin uniquement)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/_cleanup_prod_smoke_users.py <DATABASE_URL_PUBLIC>")
        print()
        print("Obtenir l'URL publique :")
        print("  Railway UI → Postgres service → Connect → Public URL")
        sys.exit(1)
    main(sys.argv[1])

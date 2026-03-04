"""
Nettoyage état DB local — pollution accumulée durant les runs de debug.

1. Suppression des vendors de test (TEST_* source) qui polluent les contraintes
2. Reset de la séquence vendor_id_seq si elle dépasse 9999

Ne touche PAS aux vendors de production (source != TEST_*).
"""
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg, psycopg.rows

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row)
conn.autocommit = True

with conn.cursor() as cur:
    # 1. Compter vendors de test
    cur.execute("SELECT COUNT(*) AS c FROM vendors WHERE source LIKE 'TEST%'")
    r = cur.fetchone()
    print(f"Vendors TEST_* : {r['c']}")

    # 2. Vérifier les séquences liées à vendor_id
    cur.execute("""
        SELECT sequence_name, last_value
        FROM information_schema.sequences s
        JOIN pg_sequences ps ON ps.sequencename = s.sequence_name
        WHERE s.sequence_schema = 'public'
          AND s.sequence_name ILIKE '%vendor%'
    """)
    seqs = cur.fetchall()
    print("Séquences vendor :")
    for s in seqs:
        print(f"  {s['sequence_name']} = {s['last_value']}")

    # 3. Supprimer vendors TEST_* avec market_signals vide (safe)
    cur.execute("""
        SELECT COUNT(*) AS ms_count FROM market_signals
        WHERE vendor_id IS NOT NULL
    """)
    r = cur.fetchone()
    print(f"market_signals avec vendor_id non-null : {r['ms_count']}")

    if r['ms_count'] == 0:
        cur.execute("DELETE FROM vendors WHERE source LIKE 'TEST%'")
        print(f"Vendors TEST_* supprimés (rowcount={cur.rowcount})")
    else:
        print("market_signals non vide — suppression vendors annulée")

    # 4. Reset séquences si valeur > 9999
    for s in seqs:
        if s['last_value'] and s['last_value'] > 9999:
            cur.execute(f"ALTER SEQUENCE {s['sequence_name']} RESTART WITH 1")
            print(f"Séquence {s['sequence_name']} réinitialisée → 1")

    # 5. Supprimer le doublon DMS-VND-BKO-9901-Z si encore présent
    cur.execute("DELETE FROM vendors WHERE vendor_id = 'DMS-VND-BKO-9901-Z' AND source LIKE 'TEST%'")
    if cur.rowcount > 0:
        print(f"Doublon DMS-VND-BKO-9901-Z supprimé")

    # 6. Vérif finale
    cur.execute("SELECT COUNT(*) AS c FROM vendors WHERE source LIKE 'TEST%'")
    r = cur.fetchone()
    print(f"Vendors TEST_* restants : {r['c']}")

conn.close()
print("Done.")

"""
scripts/apply_fk_prod.py

Applique la FK market_signals.vendor_id → vendors(id) ON DELETE RESTRICT
sur l'environnement Railway (prod).

Cette FK n'est pas dans la migration Alembic :
  La protection append-only de market_signals bloque FOR KEY SHARE
  lors des DELETE vendors en environnement local.
  Railway a des privilèges différents permettant cette FK.

Usage :
  DATABASE_URL=<prod_url> python scripts/apply_fk_prod.py

Prérequis :
  - market_signals.vendor_id doit être UUID (migration m5_fix appliquée)
  - Aucune ligne dans market_signals avec vendor_id non NULL
    pointant vers un vendor inexistant
  - Exécuter sur prod Railway uniquement
"""

import os
import sys

import psycopg


def apply_fk() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERREUR : DATABASE_URL absent")
        sys.exit(1)

    with psycopg.connect(db_url) as conn:

        # Probe : FK déjà présente ?
        row = conn.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE constraint_name = 'market_signals_vendor_id_fkey'
              AND table_name      = 'market_signals'
              AND constraint_type = 'FOREIGN KEY'
        """).fetchone()

        if row:
            print("FK market_signals_vendor_id_fkey déjà présente — skip")
            return

        # Probe : vendor_id est UUID ?
        col = conn.execute("""
            SELECT udt_name FROM information_schema.columns
            WHERE table_name  = 'market_signals'
              AND column_name = 'vendor_id'
        """).fetchone()

        if not col or col[0] != "uuid":
            print(f"ERREUR : vendor_id type = {col[0] if col else 'absent'}")
            print("Appliquer d'abord la migration m5_fix_market_signals_vendor_type")
            sys.exit(1)

        # Appliquer la FK
        conn.execute("""
            ALTER TABLE market_signals
                ADD CONSTRAINT market_signals_vendor_id_fkey
                FOREIGN KEY (vendor_id)
                REFERENCES vendors(id)
                ON DELETE RESTRICT;
        """)
        conn.commit()
        print("FK market_signals_vendor_id_fkey créée avec ON DELETE RESTRICT")


if __name__ == "__main__":
    apply_fk()

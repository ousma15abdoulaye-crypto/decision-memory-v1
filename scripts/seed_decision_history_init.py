"""
SEED — DETTE-3 M11
Initialise decision_history en historisant
les signaux CRITICAL et WATCH existants.

Strategie :
  Chaque signal CRITICAL ou WATCH dans market_signals_v2
  devient une entree decision_history decision_type='signal_alert'.
  source_ref = signal id (UUID).
  unit_price = price_avg du signal.
  decided_at = updated_at ou created_at.

Schema reel : item_id, zone_id, decision_type, unit_price,
              quantity, currency, decided_at, source_ref.

Regle rollback : conn.rollback() sur tout except.
Idempotence : skip si source_ref deja present.

Usage : DATABASE_URL=<railway> DMS_ALLOW_RAILWAY=1 \
        python scripts/seed_decision_history_init.py
"""

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


def main():
    db_url = os.environ.get("RAILWAY_DATABASE_URL", "") or os.environ.get(
        "DATABASE_URL", ""
    )
    if not db_url:
        sys.exit("STOP — DATABASE_URL absente")
    if "railway" in db_url.lower() and os.environ.get("DMS_ALLOW_RAILWAY", "0") != "1":
        sys.exit("STOP — CONTRACT-02")
    url = db_url.replace("postgresql+psycopg://", "postgresql://")

    ok = skip = err = 0

    with psycopg.connect(url, row_factory=dict_row) as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT id, item_id, zone_id, alert_level,
                   price_avg, updated_at, created_at
            FROM market_signals_v2
            WHERE alert_level IN ('CRITICAL', 'WATCH')
            ORDER BY alert_level, zone_id, item_id
        """)
        signals = cur.fetchall()

        print(f"INFO — {len(signals)} signaux CRITICAL/WATCH a historiser")

        for sig in signals:
            ref_id = str(sig["id"]) if sig.get("id") else ""
            if not ref_id:
                skip += 1
                continue

            cur.execute(
                "SELECT 1 FROM decision_history WHERE source_ref = %s",
                (ref_id,),
            )
            if cur.fetchone():
                skip += 1
                continue

            unit_price = sig.get("price_avg") or 0
            decided_at = sig.get("updated_at") or sig.get("created_at")
            if not decided_at:
                skip += 1
                continue

            try:
                cur.execute("SAVEPOINT sp_decision")
                cur.execute(
                    """
                    INSERT INTO decision_history
                        (item_id, zone_id, decision_type, unit_price,
                         quantity, currency, decided_at, source_ref)
                    VALUES (%s, %s, 'signal_alert', %s, 1.0, 'XOF', %s, %s)
                    """,
                    (
                        sig["item_id"],
                        sig["zone_id"],
                        unit_price,
                        (
                            decided_at.date()
                            if hasattr(decided_at, "date")
                            else decided_at
                        ),
                        ref_id,
                    ),
                )
                cur.execute("RELEASE SAVEPOINT sp_decision")
                ok += 1
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sp_decision")
                print(f"ERR signal {ref_id} — {e}")
                err += 1

        conn.commit()
        print("INFO — commit final")

    print(f"\nRESULTAT ok={ok} skip={skip} err={err}")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()

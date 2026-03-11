#!/usr/bin/env python3
"""
Compute Market Signals V1.1 -- batch ou unitaire.
Usage :
  python scripts/compute_market_signals.py
  python scripts/compute_market_signals.py --item-id X --zone-id Y
  python scripts/compute_market_signals.py --dry-run
"""

import argparse
import logging
import os
import sys
from datetime import datetime

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, ".")

try:
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

from src.couche_a.market.signal_engine import SignalEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def env() -> str:
    u = os.environ.get("DATABASE_URL", "")
    if not u:
        raise SystemExit("DATABASE_URL absent")
    return u.replace("postgresql+psycopg://", "postgresql://")


def get_scope(cur) -> list[tuple[str, str]]:
    """Borne : tracked items x tracked zones."""
    cur.execute("""
        SELECT tmi.item_id, tmz.zone_id
        FROM public.tracked_market_items tmi
        CROSS JOIN public.tracked_market_zones tmz
        ORDER BY tmi.item_id, tmz.zone_id
    """)
    return [(r["item_id"], r["zone_id"]) for r in cur.fetchall()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--item-id")
    p.add_argument("--zone-id")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    db = env()
    eng = SignalEngine(db, allow_railway=True)
    con = psycopg.connect(db, row_factory=dict_row)
    cur = con.cursor()
    mon = datetime.now().month

    scope = (
        [(args.item_id, args.zone_id)]
        if args.item_id and args.zone_id
        else get_scope(cur)
    )
    logger.info("Scope : %d paires", len(scope))

    ok = err = empty = prop = 0

    for item_id, zone_id in scope:
        try:
            cur.execute(
                "SELECT taxo_l3 FROM couche_b.procurement_dict_items WHERE item_id = %s LIMIT 1",
                (item_id,),
            )
            tr = cur.fetchone()
            taxo = tr["taxo_l3"] if tr else None

            r = eng.compute_signal(item_id, zone_id, month=mon, taxo_l3=taxo)

            if r.signal_quality == "empty":
                empty += 1
                continue

            if r.is_propagated:
                prop += 1

            if not args.dry_run:
                eng.persist_signal(r, con)

            ok += 1

            if r.alert_level in ("CRITICAL", "WARNING"):
                logger.warning(
                    "ALERT %s | %s x %s | raw=%.0f adj=%.0f res=%.1f%%",
                    r.alert_level,
                    item_id[:20],
                    zone_id[:20],
                    r.price_raw or 0,
                    r.price_seasonal_adj or 0,
                    r.residual_pct or 0,
                )

        except Exception as e:
            err += 1
            logger.error("ERR %s x %s: %s", item_id, zone_id, e)

    con.close()
    logger.info("DONE ok=%d empty=%d prop=%d err=%d", ok, empty, prop, err)
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()

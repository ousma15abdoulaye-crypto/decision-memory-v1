#!/usr/bin/env python3
"""MRD-5 — Backfill item_code.

Format : {PREFIX}-{YYYYMM}-{SEQ6}
PREFIX = MC | IC | SD | LG (derive de birth_source)
YYYYMM = annee+mois de birth_timestamp
SEQ6   = sequence dans le run (ORDER BY item_id — stable, pas metier)

[IS-09] item_code jamais derive d'une taxonomie
[IS-10] item_code immuable apres creation
[IS-11] item_id jamais recalcule

Note schema : PK = item_id (TEXT), pas item_uid

Usage :
  python scripts/mrd5_backfill_item_code.py --dry-run
  python scripts/mrd5_backfill_item_code.py --execute
"""

import argparse
import os
import sys
import uuid
from datetime import UTC, datetime

import psycopg
from psycopg.rows import dict_row


def check_env() -> str:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
        db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        raise SystemExit("DATABASE_URL absente - verifier .env")
    if "railway" in db_url.lower() or "rlwy" in db_url.lower():
        raise SystemExit("CONTRACT-02 VIOLE - DATABASE_URL pointe Railway - interdit")
    return db_url.replace("postgresql+psycopg://", "postgresql://", 1)


def get_prefix(birth_source: str | None) -> str:
    if not birth_source:
        return "LG"
    bs = birth_source.strip().lower()
    if bs in ("mercuriale", "mercuriales"):
        return "MC"
    if bs == "imc":
        return "IC"
    if bs in ("seed", "manual"):
        return "SD"
    return "LG"


def make_item_code(prefix: str, birth_ts: datetime | None, seq: int) -> str:
    if birth_ts is None:
        birth_ts = datetime.now(UTC)
    yyyymm = birth_ts.strftime("%Y%m")
    seq6 = str(seq).zfill(6)
    return f"{prefix}-{yyyymm}-{seq6}"


def run(db_url: str, dry_run: bool) -> dict:
    run_id = str(uuid.uuid4())
    mode = "DRY-RUN" if dry_run else "EXECUTE"

    print(f"\n{'=' * 55}")
    print(f"MRD-5 BACKFILL ITEM_CODE - {mode}")
    print(f"run_id : {run_id}")
    print(f"{'=' * 55}")

    conn = psycopg.connect(db_url, row_factory=dict_row)
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) AS n
        FROM couche_b.procurement_dict_items
        WHERE item_code IS NULL AND active = TRUE
    """)
    total_sans_code = cur.fetchone()["n"]
    print(f"\nItems sans item_code : {total_sans_code}")

    if total_sans_code == 0:
        print("Backfill deja complet - aucun item a traiter")
        conn.close()
        return {
            "mode": mode,
            "total": 0,
            "ok": 0,
            "errors": [],
            "verdict": "PASS",
        }

    # ORDER BY item_id — stable, non derive du metier
    cur.execute("""
        SELECT item_id, birth_source, birth_timestamp
        FROM couche_b.procurement_dict_items
        WHERE item_code IS NULL AND active = TRUE
        ORDER BY item_id
    """)
    items = cur.fetchall()

    ok = 0
    errors = []
    seq = 1

    for item in items:
        prefix = get_prefix(item["birth_source"])
        item_code = make_item_code(prefix, item["birth_timestamp"], seq)

        # Garantir unicite — incrementer si collision
        cur.execute(
            """
            SELECT COUNT(*) AS n
            FROM couche_b.procurement_dict_items
            WHERE item_code = %s AND active = TRUE
            """,
            (item_code,),
        )
        while cur.fetchone()["n"] > 0:
            seq += 1
            item_code = make_item_code(prefix, item["birth_timestamp"], seq)
            cur.execute(
                """
                SELECT COUNT(*) AS n
                FROM couche_b.procurement_dict_items
                WHERE item_code = %s AND active = TRUE
                """,
                (item_code,),
            )

        if not dry_run:
            try:
                cur.execute(
                    """
                    UPDATE couche_b.procurement_dict_items
                    SET item_code = %s
                    WHERE item_id    = %s
                      AND item_code IS NULL
                    """,
                    (item_code, item["item_id"]),
                )
                ok += 1
            except Exception as e:
                errors.append(f"item_id={item['item_id']} - {e}")
        else:
            ok += 1

        seq += 1

    if not dry_run:
        conn.commit()

    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE active = TRUE)                  AS total,
            COUNT(*) FILTER (WHERE item_code IS NOT NULL
                              AND active = TRUE)                   AS avec_code,
            COUNT(*) FILTER (WHERE item_code IS NULL
                              AND active = TRUE)                   AS sans_code
        FROM couche_b.procurement_dict_items
    """)
    r = cur.fetchone()

    print(f"\nRESULTAT {mode} :")
    print(f"  ok={ok} errors={len(errors)}")
    print(
        f"  total_actifs={r['total']}"
        f" avec_code={r['avec_code']}"
        f" sans_code={r['sans_code']}"
    )

    if errors:
        print("\nERREURS :")
        for e in errors:
            print(f"  {e}")

    verdict = len(errors) == 0 and (dry_run or r["sans_code"] == 0)
    print(f"\nVERDICT : {'PASS' if verdict else 'FAIL'}")

    conn.close()
    return {
        "mode": mode,
        "total": total_sans_code,
        "ok": ok,
        "errors": errors,
        "avec_code": r["avec_code"],
        "sans_code": r["sans_code"],
        "verdict": "PASS" if verdict else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("Usage : --dry-run | --execute")
        sys.exit(1)

    db_url = check_env()
    results = run(db_url, dry_run=args.dry_run)
    sys.exit(0 if results["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()

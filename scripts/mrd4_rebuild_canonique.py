#!/usr/bin/env python3
"""MRD-4 Pipeline rebuild canonique.

INV-05 : Rebuild = UPSERT fingerprint. Jamais DELETE+INSERT.
INV-04 : Identite stable.

Fingerprint (peer review) :
  sha256(normalize(label_fr)|source_type)
  source_id EXCLU - identifiant pas identite

Usage :
  python scripts/mrd4_rebuild_canonique.py --dry-run
  python scripts/mrd4_rebuild_canonique.py --execute
"""

import argparse
import hashlib
import os
import re
import sys
import uuid
from datetime import UTC, datetime

import psycopg
from psycopg.rows import dict_row


def check_env() -> str:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        # Charger .env
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


def normalize(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip().lower())


def compute_fingerprint(label: str, source_type: str) -> str:
    """sha256(normalize(label_fr)|source_type) - source_id exclu."""
    st = (source_type or "unknown").strip().lower()
    raw = f"{normalize(label)}|{st}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def run(db_url: str, dry_run: bool) -> dict:
    run_id = str(uuid.uuid4())
    run_ts = datetime.now(UTC)
    mode = "DRY-RUN" if dry_run else "EXECUTE"

    print(f"\n{'=' * 55}")
    print(f"MRD-4 REBUILD CANONIQUE - {mode}")
    print(f"run_id : {run_id}")
    print(f"ts     : {run_ts.isoformat()}")
    print(f"{'=' * 55}")

    conn = psycopg.connect(db_url, row_factory=dict_row)
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items" " WHERE active=TRUE"
    )
    items_avant = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) AS n FROM couche_b.procurement_dict_aliases")
    aliases_avant = cur.fetchone()["n"]

    cur.execute(
        "SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items"
        " WHERE fingerprint IS NULL AND active=TRUE"
    )
    sans_fp_avant = cur.fetchone()["n"]

    print(
        f"\nAVANT : items_actifs={items_avant}"
        f" aliases={aliases_avant}"
        f" sans_fingerprint={sans_fp_avant}"
    )

    cur.execute("""
        SELECT item_id, label_fr, birth_source
        FROM couche_b.procurement_dict_items
        WHERE fingerprint IS NULL
          AND active = TRUE
          AND label_fr IS NOT NULL
        ORDER BY item_id
    """)
    items_sans_fp = cur.fetchall()
    print(f"\nBackfill fingerprint : {len(items_sans_fp)} items")

    backfill_ok = 0
    backfill_skip = 0
    collisions = []
    errors = []

    for item in items_sans_fp:
        label = item["label_fr"]
        source_type = item["birth_source"] or "unknown"
        fp = compute_fingerprint(label, source_type)

        cur.execute(
            """
            SELECT item_id FROM couche_b.procurement_dict_items
            WHERE fingerprint = %s AND active = TRUE AND item_id != %s
            """,
            (fp, item["item_id"]),
        )
        existing = cur.fetchone()

        if existing:
            collisions.append(
                {
                    "fp": fp[:16] + "...",
                    "item_id_courant": item["item_id"],
                    "item_id_existant": existing["item_id"],
                    "label": label,
                }
            )
            backfill_skip += 1
            continue

        if not dry_run:
            try:
                cur.execute(
                    """
                    UPDATE couche_b.procurement_dict_items
                    SET fingerprint     = %s,
                        birth_source    = %s,
                        birth_run_id    = %s::uuid,
                        birth_timestamp = COALESCE(birth_timestamp, %s)
                    WHERE item_id     = %s
                      AND fingerprint IS NULL
                    """,
                    (fp, source_type, run_id, run_ts, item["item_id"]),
                )
                backfill_ok += 1
            except Exception as e:
                errors.append(f"item_id={item['item_id']} - {e}")
        else:
            backfill_ok += 1

    if not dry_run:
        conn.commit()

    print(
        f"Backfill : ok={backfill_ok}"
        f" skip_collision={backfill_skip}"
        f" errors={len(errors)}"
    )

    if collisions:
        print(f"\nCOLLISIONS ({len(collisions)}) :")
        for c in collisions:
            print(
                f"  fp={c['fp']}"
                f" label='{c['label']}'"
                f" id_courant={c['item_id_courant'][:8]}"
                f" id_existant={c['item_id_existant'][:8]}"
            )

    if errors:
        print(f"\nERREURS ({len(errors)}) :")
        for e in errors:
            print(f"  {e}")

    cur.execute(
        "SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items" " WHERE active=TRUE"
    )
    items_apres = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) AS n FROM couche_b.procurement_dict_aliases")
    aliases_apres = cur.fetchone()["n"]

    cur.execute(
        "SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items"
        " WHERE fingerprint IS NULL AND active=TRUE"
    )
    sans_fp_apres = cur.fetchone()["n"]

    print(
        f"\nAPRES  : items_actifs={items_apres}"
        f" aliases={aliases_apres}"
        f" sans_fingerprint={sans_fp_apres}"
    )

    alias_rate = aliases_apres / aliases_avant if aliases_avant > 0 else 1.0
    destructive_loss = max(0, items_avant - items_apres)
    dup_identity = len(collisions)

    print(f"\n{'=' * 55}")
    print(f"METRIQUES VERDICT - {mode}")
    print(f"{'=' * 55}")

    alias_ok = alias_rate >= 0.99
    loss_ok = destructive_loss == 0
    dup_ok = dup_identity == 0

    print(
        f"alias_preservation_rate : {alias_rate:.4f}"
        f" {'ok' if alias_ok else 'STOP-04'}"
    )
    print(
        f"destructive_loss        : {destructive_loss}"
        f" {'ok' if loss_ok else 'STOP-06'}"
    )
    print(
        f"duplicate_identity      : {dup_identity}" f" {'ok' if dup_ok else 'STOP-05'}"
    )
    print(
        f"sans_fp_restant         : {sans_fp_apres}"
        f" {'ok' if sans_fp_apres == 0 else 'backfill incomplet'}"
    )

    verdict = alias_ok and loss_ok and dup_ok
    print(f"\nVERDICT : {'PASS' if verdict else 'FAIL'}")

    if not verdict:
        print("\nSTOPS DETECTES - ne pas commiter - poster au CTO")

    conn.close()

    return {
        "mode": mode,
        "run_id": run_id,
        "items_avant": items_avant,
        "items_apres": items_apres,
        "aliases_avant": aliases_avant,
        "aliases_apres": aliases_apres,
        "alias_preservation_rate": alias_rate,
        "destructive_loss": destructive_loss,
        "duplicate_identity": dup_identity,
        "sans_fp_restant": sans_fp_apres,
        "collisions": collisions,
        "errors": errors,
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

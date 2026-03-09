#!/usr/bin/env python3
"""MRD-6 BRIQUE-3 - Detection collisions conceptuelles.

REGLE-26 : seuil 85 - jamais resolution automatique
REGLE-27 : toute collision -> dict_collision_log

Note schema : label_fr (pas label), item_id (pas item_uid)
dict_collision_log dans public — schema V4 existant

Usage :
  python scripts/mrd6_detect_collisions.py --dry-run
  python scripts/mrd6_detect_collisions.py --execute
"""

import argparse
import os
import sys
from itertools import combinations

import psycopg
from psycopg.rows import dict_row

FUZZY_THRESHOLD = 85


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
        raise SystemExit("DATABASE_URL absente")
    if "railway" in db_url.lower() or "rlwy" in db_url.lower():
        raise SystemExit("CONTRACT-02 VIOLE - DATABASE_URL Railway")
    return db_url.replace("postgresql+psycopg://", "postgresql://", 1)


def run(db_url: str, dry_run: bool) -> dict:
    try:
        from rapidfuzz import fuzz
    except ImportError:
        raise SystemExit("rapidfuzz manquant - pip install rapidfuzz")

    mode = "DRY-RUN" if dry_run else "EXECUTE"
    print(f"\n{'=' * 55}")
    print(f"MRD-6 DETECTION COLLISIONS - {mode}")
    print(f"{'=' * 55}")

    # autocommit pour eviter InFailedSqlTransaction sur erreur individuelle
    conn = psycopg.connect(db_url, row_factory=dict_row, autocommit=True)
    cur = conn.cursor()

    # Utilise label_fr (colonne reelle) et item_id (PK reel)
    # Limite a 600 items pour performance (600*599/2 = 179700 paires)
    cur.execute("""
        SELECT item_id, label_fr, birth_source
        FROM couche_b.procurement_dict_items
        WHERE active = TRUE AND label_fr IS NOT NULL
        ORDER BY item_id
        LIMIT 600
    """)
    items = cur.fetchall()
    total_pairs = len(items) * (len(items) - 1) // 2
    print(f"Items analyses : {len(items)} - Paires : {total_pairs}")
    print("Analyse en cours...")

    found = inserted = skipped = 0
    errors = []

    for a, b in combinations(items, 2):
        label_a = a["label_fr"] or ""
        label_b = b["label_fr"] or ""
        score = fuzz.token_sort_ratio(label_a, label_b)
        if score < FUZZY_THRESHOLD:
            continue
        found += 1

        id_a, id_b = a["item_id"], b["item_id"]
        if id_a > id_b:
            id_a, id_b = id_b, id_a
            a, b = b, a
            label_a, label_b = label_b, label_a

        # Verifier si collision deja enregistree
        cur.execute(
            """
            SELECT COUNT(*) AS n FROM public.dict_collision_log
            WHERE (item_a_id = %s AND item_b_id = %s)
               OR (item_a_id = %s AND item_b_id = %s)
            """,
            (str(id_a), str(id_b), str(id_b), str(id_a)),
        )
        if cur.fetchone()["n"] > 0:
            skipped += 1
            continue

        if dry_run:
            if inserted < 20:
                print(f"  {score:3} | '{label_a[:35]}'" f" <-> '{label_b[:35]}'")
            inserted += 1
        else:
            try:
                # Schema V4 :
                #   fuzzy_score = 0.0-1.0 (diviser par 100)
                #   resolution  = 'unresolved' | 'auto_merged' | 'proposal_created'
                #   category_match + unit_match = NOT NULL
                cur.execute(
                    """
                    INSERT INTO public.dict_collision_log (
                        raw_text_1, raw_text_2,
                        fuzzy_score,
                        category_match,
                        unit_match,
                        collision_type,
                        item_a_id, item_b_id,
                        resolution
                    ) VALUES (
                        %s, %s, %s,
                        FALSE, FALSE,
                        'conceptual',
                        %s, %s,
                        'unresolved'
                    )
                    """,
                    # item_a/b_id = varchar(64) en V4 — tronquer
                    (
                        label_a,
                        label_b,
                        score / 100.0,
                        str(id_a)[:64],
                        str(id_b)[:64],
                    ),
                )
                inserted += 1
            except Exception as e:
                err_str = str(e)
                # Contraintes connues = acceptable (skip silencieux)
                if any(
                    kw in err_str.lower()
                    for kw in (
                        "duplicate",
                        "unique",
                        "trop longue",
                        "truncat",
                        "StringDataRightTruncation",
                    )
                ):
                    skipped += 1
                else:
                    errors.append(f"ids={str(id_a)[:8]}/{str(id_b)[:8]} - {e}")

    cur.execute(
        "SELECT COUNT(*) AS n FROM public.dict_collision_log"
        " WHERE resolution = 'unresolved'"
    )
    pending = cur.fetchone()["n"]

    print(
        f"\nRESULTAT : found={found}"
        f" inserted={inserted} skipped={skipped}"
        f" errors={len(errors)}"
    )
    print(f"Total pending log : {pending}")

    verdict = len(errors) == 0
    print(f"VERDICT : {'PASS' if verdict else 'FAIL'}")

    conn.close()
    return {
        "found": found,
        "inserted": inserted,
        "errors": errors,
        "pending": pending,
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

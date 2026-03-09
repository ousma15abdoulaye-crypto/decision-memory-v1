#!/usr/bin/env python3
"""MRD-6 BRIQUE-1 - Application taxonomie depuis corpus reel.

INV-07 : taxonomie APRES registre - jamais avant
Source  : docs/data/MRD6_TAXONOMY_V1.md (cree ETAPE 3)

Note schema : label_fr (pas label), item_id (pas item_uid)

Usage :
  python scripts/mrd6_apply_taxonomy.py --dry-run
  python scripts/mrd6_apply_taxonomy.py --apply
"""

import argparse
import os
import sys

import psycopg
from psycopg.rows import dict_row

TAXO_VERSION = "1.0"
TAXO_FILE = "docs/data/MRD6_TAXONOMY_V1.md"


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


def load_rules() -> list[dict]:
    if not os.path.exists(TAXO_FILE):
        raise SystemExit(f"{TAXO_FILE} absent - " "creer docs/data/MRD6_TAXONOMY_V1.md")
    rules = []
    with open(TAXO_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                parts = dict(p.split(":", 1) for p in line.split("|"))
                if "L1" in parts and "pattern" in parts:
                    rules.append(
                        {
                            "l1": parts.get("L1", "").strip(),
                            "l2": parts.get("L2", "").strip(),
                            "l3": parts.get("L3", "").strip(),
                            "pattern": parts.get("pattern", "").strip().lower(),
                        }
                    )
            except Exception:
                continue
    print(f"Regles chargees : {len(rules)}")
    return rules


def run(db_url: str, dry_run: bool) -> dict:
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"\n{'=' * 55}")
    print(f"MRD-6 APPLY TAXONOMY V1 - {mode}")
    print(f"{'=' * 55}")

    rules = load_rules()
    conn = psycopg.connect(db_url, row_factory=dict_row)
    cur = conn.cursor()

    # Utilise label_fr (colonne label reelle)
    cur.execute("""
        SELECT item_id, label_fr
        FROM couche_b.procurement_dict_items
        WHERE active = TRUE AND label_fr IS NOT NULL
    """)
    items = cur.fetchall()
    print(f"Items a classifier : {len(items)}")

    classified = 0
    unclassified = 0
    updates = []

    for item in items:
        label_low = (item["label_fr"] or "").lower()
        matched = None
        for rule in rules:
            if rule["pattern"] and rule["pattern"] in label_low:
                matched = rule
                break
        if matched:
            updates.append(
                {
                    "item_id": item["item_id"],
                    "l1": matched["l1"],
                    "l2": matched["l2"],
                    "l3": matched["l3"],
                }
            )
            classified += 1
        else:
            unclassified += 1

    coverage = classified / len(items) if items else 0
    print(f"Classifies    : {classified}")
    print(f"Non classifies: {unclassified}")
    ok_str = "ok >= 85%" if coverage >= 0.85 else "STOP-06 < 85%"
    print(f"Coverage gate : {coverage:.2%} {ok_str}")

    if coverage < 0.85 and not dry_run:
        print("\nCoverage < 85% - enrichir MRD6_TAXONOMY_V1.md " "et relancer")
        conn.close()
        sys.exit(1)

    if not dry_run:
        for u in updates:
            cur.execute(
                """
                UPDATE couche_b.procurement_dict_items
                SET taxo_l1      = %s,
                    taxo_l2      = %s,
                    taxo_l3      = %s,
                    taxo_version = %s
                WHERE item_id = %s
                """,
                (u["l1"], u["l2"], u["l3"], TAXO_VERSION, u["item_id"]),
            )
        conn.commit()

        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE taxo_l1 IS NOT NULL
                                  AND active = TRUE)   AS avec_taxo,
                COUNT(*) FILTER (WHERE taxo_l1 IS NULL
                                  AND active = TRUE)   AS sans_taxo
            FROM couche_b.procurement_dict_items
        """)
        r = cur.fetchone()
        print(
            f"\nApres apply : "
            f"avec_taxo={r['avec_taxo']} "
            f"sans_taxo={r['sans_taxo']}"
        )

    conn.close()
    verdict = coverage >= 0.85
    print(f"\nVERDICT : {'PASS' if verdict else 'FAIL'}")
    return {
        "classified": classified,
        "unclassified": unclassified,
        "coverage": coverage,
        "verdict": "PASS" if verdict else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and not args.apply:
        print("Usage : --dry-run | --apply")
        sys.exit(1)
    db_url = check_env()
    results = run(db_url, dry_run=args.dry_run)
    sys.exit(0 if results["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()

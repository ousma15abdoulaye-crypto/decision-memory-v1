#!/usr/bin/env python3
"""
Sync couche_b.procurement_dict_items local -> Railway.
Strategie : TRUNCATE + COPY via INSERT batches de 100.
Neutralise les FK en nullifiant family_id et default_unit.

Usage :
  python scripts/sync_dict_local_to_railway.py --dry-run
  python scripts/sync_dict_local_to_railway.py --apply
"""
import os
import sys
import argparse
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row


def get_urls() -> tuple[str, str]:
    local = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
    railway = os.environ.get("RAILWAY_DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
    if not local:
        raise SystemExit("DATABASE_URL absent")
    if not railway:
        raise SystemExit("RAILWAY_DATABASE_URL absent")
    if "railway" in local.lower():
        raise SystemExit("ERREUR : DATABASE_URL pointe Railway")
    return local, railway


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    if not args.dry_run and not args.apply:
        print("Usage : --dry-run ou --apply")
        sys.exit(1)

    local_url, railway_url = get_urls()

    # Lire items depuis local
    src = psycopg.connect(local_url, row_factory=dict_row, autocommit=True)
    cur_src = src.cursor()
    cur_src.execute("""
        SELECT item_id, label_fr, label_en,
               active, canonical_slug, dict_version,
               confidence_score, human_validated,
               taxo_l1, taxo_l2, taxo_l3, taxo_version,
               item_code, fingerprint, birth_source,
               label_status, quality_score, item_type
        FROM couche_b.procurement_dict_items
        WHERE active = TRUE
          AND item_id NOT LIKE '\_%'
        ORDER BY item_id
    """)
    items = cur_src.fetchall()
    src.close()
    print(f"Items locaux actifs (hors test) : {len(items)}")

    if args.dry_run:
        print("\nDRY-RUN — 5 premiers :")
        for it in items[:5]:
            print(f"  {it['item_id'][:50]} | {it['label_fr'][:40]}")
        print(f"\n  Total : {len(items)}")
        return

    # Vérifier colonnes Railway
    dst = psycopg.connect(railway_url, row_factory=dict_row, autocommit=True)
    cur_dst = dst.cursor()

    cur_dst.execute("""
        SELECT column_name, is_nullable FROM information_schema.columns
        WHERE table_schema='couche_b' AND table_name='procurement_dict_items'
        ORDER BY ordinal_position
    """)
    railway_schema = {r["column_name"]: r["is_nullable"] for r in cur_dst.fetchall()}
    railway_cols = set(railway_schema.keys())

    # Trouver une unite par defaut sur Railway (pour default_unit NOT NULL)
    default_unit = None
    try:
        cur_dst.execute("""
            SELECT unit_code FROM couche_b.procurement_dict_units LIMIT 1
        """)
        r = cur_dst.fetchone()
        if r:
            default_unit = r["unit_code"]
    except Exception:
        pass
    if not default_unit:
        default_unit = "unite"
    print(f"Unite par defaut Railway : {default_unit}")

    # Colonnes sans FK problematiques
    insert_cols = [
        c for c in [
            "item_id", "label_fr", "label_en", "active",
            "canonical_slug", "dict_version", "confidence_score",
            "human_validated", "taxo_l1", "taxo_l2", "taxo_l3",
            "taxo_version", "item_code", "fingerprint", "birth_source",
            "label_status", "quality_score", "item_type",
        ]
        if c in railway_cols
    ]
    # Ajouter default_unit si colonne presente
    if "default_unit" in railway_cols:
        insert_cols.append("default_unit")
    print(f"Colonnes a inserer ({len(insert_cols)}) : {insert_cols}")

    cols_str = ", ".join(insert_cols)
    placeholders = ", ".join(f"%({c})s" for c in insert_cols)
    update_str = ", ".join(
        f"{c} = EXCLUDED.{c}" for c in insert_cols if c != "item_id"
    )
    sql = f"""
        INSERT INTO couche_b.procurement_dict_items ({cols_str})
        VALUES ({placeholders})
        ON CONFLICT (item_id) DO UPDATE SET {update_str}
    """

    # Insert par batch de 50 — gère la latence Railway
    BATCH = 50
    ok = err = 0
    for i in range(0, len(items), BATCH):
        batch = items[i : i + BATCH]
        for it in batch:
            vals = {c: it.get(c) for c in insert_cols}
            # Fallback default_unit si NULL
            if "default_unit" in vals and vals["default_unit"] is None:
                vals["default_unit"] = default_unit
            try:
                cur_dst.execute(sql, vals)
                ok += 1
            except Exception as e:
                if err < 5:
                    print(f"  ERR {str(it.get('item_id',''))[:35]}: {e}")
                err += 1
        pct = int((i + len(batch)) / len(items) * 100)
        print(f"  {i+len(batch)}/{len(items)} ({pct}%) ok={ok} err={err}", flush=True)

    # Vérification finale
    cur_dst.execute("SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items WHERE active=TRUE")
    n = cur_dst.fetchone()["n"]
    dst.close()

    print(f"\nRESULTAT : ok={ok} err={err}")
    print(f"Railway procurement_dict_items actifs : {n}")
    sys.exit(1 if err > 10 else 0)


if __name__ == "__main__":
    main()

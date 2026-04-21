#!/usr/bin/env python3
"""
Creer et peupler mercurials_item_map sur Railway.

Table : mercurials_item_map
  item_canonical TEXT  (cle mercurials)
  dict_item_id   TEXT  (FK procurement_dict_items.item_id)
  score          NUMERIC (confiance bigram)
  confiance      TEXT   (AUTO|REVUE)

Usage :
  python scripts/create_mercurials_mapping.py --create
  python scripts/create_mercurials_mapping.py --load
  python scripts/create_mercurials_mapping.py --verify
"""

import os
import sys
import csv
import argparse
import io
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row

CSV_PATH = "mercurials_mapping_proposals.csv"


def get_url() -> str:
    u = os.environ.get("RAILWAY_DATABASE_URL", "")
    if not u:
        u = os.environ.get("DATABASE_URL", "")
    if not u:
        raise SystemExit("DATABASE_URL / RAILWAY_DATABASE_URL absente")
    return u.replace("postgresql+psycopg://", "postgresql://")


def do_create(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.mercurials_item_map (
            item_canonical  TEXT PRIMARY KEY,
            dict_item_id    TEXT NOT NULL
                            REFERENCES couche_b.procurement_dict_items(item_id),
            score           NUMERIC(5,3),
            confiance       TEXT
        )
    """)
    conn.commit()
    print("Table mercurials_item_map creee (ou deja existante)")


def do_load(conn):
    if not Path(CSV_PATH).exists():
        raise SystemExit(f"CSV absent : {CSV_PATH}")

    # Lire CSV en UTF-8
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Garder uniquement OUI (AUTO)
    valides = [r for r in rows if r.get("valider_oui_non", "").upper() == "OUI"]
    print(f"Mappings a charger : {len(valides)} (sur {len(rows)} total)")

    cur = conn.cursor()
    ok = err = 0
    for r in valides:
        try:
            cur.execute(
                """
                INSERT INTO public.mercurials_item_map
                    (item_canonical, dict_item_id, score, confiance)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (item_canonical) DO UPDATE SET
                    dict_item_id = EXCLUDED.dict_item_id,
                    score        = EXCLUDED.score,
                    confiance    = EXCLUDED.confiance
            """,
                (
                    r["item_canonical"],
                    r["item_id_propose"],
                    float(r["score"]),
                    r["confiance"],
                ),
            )
            ok += 1
        except Exception as e:
            if err < 5:
                msg = repr(r.get("item_canonical", ""))[:50]
                print(f"  ERR {msg}: {e}")
            err += 1

    conn.commit()
    print(f"Charge : ok={ok} err={err}")


def do_verify(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM public.mercurials_item_map")
    n = cur.fetchone()["n"]
    print(f"mercurials_item_map : {n} mappings")

    cur.execute("""
        SELECT COUNT(DISTINCT m.item_canonical) AS canonical_total,
               COUNT(DISTINCT map.item_canonical) AS canonical_mapped
        FROM mercurials m
        LEFT JOIN public.mercurials_item_map map
          ON map.item_canonical = m.item_canonical
    """)
    r = cur.fetchone()
    mapped_pct = (
        r["canonical_mapped"] / r["canonical_total"] * 100
        if r["canonical_total"] > 0
        else 0
    )
    print(
        f"item_canonical Railway : {r['canonical_total']} total, "
        f"{r['canonical_mapped']} mappes ({mapped_pct:.1f}%)"
    )

    # Estimer lignes mercurials joignables
    cur.execute("""
        SELECT COUNT(*) AS n
        FROM mercurials m
        JOIN public.mercurials_item_map map
          ON map.item_canonical = m.item_canonical
    """)
    r2 = cur.fetchone()
    total_merc = 27396
    pct2 = r2["n"] / total_merc * 100
    print(f"Lignes mercurials joignables : {r2['n']}/{total_merc} ({pct2:.1f}%)")

    # Sample
    cur.execute("""
        SELECT map.item_canonical, map.dict_item_id,
               map.score, di.label_fr, di.taxo_l1
        FROM public.mercurials_item_map map
        JOIN couche_b.procurement_dict_items di
          ON di.item_id = map.dict_item_id
        LIMIT 5
    """)
    print("\nSample mappings :")
    for r in cur.fetchall():
        print(
            f"  {str(r['item_canonical'])[:35]:35s} -> "
            f"{str(r['label_fr'])[:35]:35s} "
            f"score={r['score']} taxo={r['taxo_l1']}"
        )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--create", action="store_true")
    p.add_argument("--load", action="store_true")
    p.add_argument("--verify", action="store_true")
    args = p.parse_args()

    url = get_url()
    conn = psycopg.connect(url, row_factory=dict_row)

    if args.create:
        do_create(conn)
    if args.load:
        do_load(conn)
    if args.verify:
        do_verify(conn)

    if not any([args.create, args.load, args.verify]):
        print("Usage : --create | --load | --verify")
        sys.exit(1)

    conn.close()


if __name__ == "__main__":
    main()

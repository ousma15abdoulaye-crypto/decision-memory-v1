#!/usr/bin/env python3
"""
Seed tracked scope + 3 baskets GLOBAL_CORE multi-secteur.
ETA_V1 §2 : États / Mines / ONG / Privé à volume élevé.
Usage : python scripts/seed_tracked_market_scope.py

Adaptation schéma réel : geo_master n'a pas de colonne code.
Mapping FEWS (ML-X) → geo_master par name.
"""

import os
import sys

try:
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row

PATTERNS = [
    "riz",
    "huile",
    "sel",
    "sucre",
    "farine",
    "mil",
    "gasoil",
    "essence",
    "carburant",
    "diesel",
    "transport",
    "fret",
    "ciment",
    "fer",
    "tôle",
    "bois",
    "gravier",
    "médicament",
    "savon",
    "papier",
    "cartouche",
    "générateur",
    "pompe",
]

# Mapping FEWS → geo_master.name (pas de colonne code)
ZONE_NAME_MAP = {
    "ML-1": "Bamako",
    "ML-2": "Gao",
    "ML-6": "Kidal",
    "ML-7": "Mopti",
    "ML-8": "Tombouctou",
    "ML-9": "Ménaka",
}

BASKETS = [
    {
        "name": "Panier référence humanitaire NFI",
        "desc": "NFI + alimentation — ONG / urgence / terrain",
        "type": "humanitarian_nfi",
        "patterns": ["riz", "huile", "sel", "savon"],
    },
    {
        "name": "Panier référence construction",
        "desc": "Matériaux gros œuvre — État/mines/BTP/infra",
        "type": "construction_materials",
        "patterns": ["ciment", "fer", "tôle", "bois"],
    },
    {
        "name": "Panier référence administration",
        "desc": "Opérationnel + carburant — admin/privé",
        "type": "office_supplies",
        "patterns": ["papier", "cartouche", "gasoil", "transport"],
    },
]


def main():
    db = os.environ.get("DATABASE_URL", "")
    if not db:
        raise SystemExit("DATABASE_URL absente")
    if "railway" in db.lower():
        raise SystemExit("CONTRACT-02")
    url = db.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(url, row_factory=dict_row)
    cur = conn.cursor()

    # ── Items tracked ─────────────────────────────────
    items, seen = [], set()
    for p in PATTERNS:
        cur.execute(
            """
            SELECT item_id, label_fr
            FROM couche_b.procurement_dict_items
            WHERE LOWER(label_fr) LIKE %s AND active = TRUE
            LIMIT 3
            """,
            (f"%{p.lower()}%",),
        )
        for r in cur.fetchall():
            if r["item_id"] not in seen:
                seen.add(r["item_id"])
                items.append(r)

    print(f"Items trouvés : {len(items)}")
    if len(items) < 10:
        print("WARN : < 10 items — vérifier corpus")

    items_ok = 0
    for it in items:
        try:
            cur.execute(
                """
                INSERT INTO public.tracked_market_items
                    (item_id, priority, notes)
                VALUES (%s, 'strategic', %s)
                ON CONFLICT (item_id) DO NOTHING
                """,
                (it["item_id"], f"Multi-secteur : {it['label_fr']}"),
            )
            items_ok += 1
        except Exception as e:
            print(f"  SKIP {it['label_fr']} : {e}")

    # ── Zones tracked ─────────────────────────────────
    zones, zones_ok = [], 0
    for fews_code, zone_name in ZONE_NAME_MAP.items():
        cur.execute(
            "SELECT id, name FROM public.geo_master WHERE name = %s LIMIT 1",
            (zone_name,),
        )
        r = cur.fetchone()
        if r:
            zones.append({"id": r["id"], "name": r["name"], "fews": fews_code})
        else:
            print(f"  ZONE ABSENTE : {fews_code} ({zone_name})")

    for z in zones:
        try:
            cur.execute(
                """
                INSERT INTO public.tracked_market_zones
                    (zone_id, priority, notes)
                VALUES (%s, 'strategic', %s)
                ON CONFLICT (zone_id) DO NOTHING
                """,
                (z["id"], f"Zone stratégique FEWS {z['fews']} : {z['name']}"),
            )
            zones_ok += 1
        except Exception as e:
            print(f"  SKIP {z['fews']} : {e}")

    # ── Baskets GLOBAL_CORE ────────────────────────────
    baskets_ok = 0
    basket_item_errors = 0
    for b in BASKETS:
        cur.execute(
            """
            INSERT INTO public.market_baskets
                (name, description, basket_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id
            """,
            (b["name"], b["desc"], b["type"]),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                "SELECT id FROM public.market_baskets WHERE name = %s",
                (b["name"],),
            )
            row = cur.fetchone()
        bid = row["id"]
        baskets_ok += 1
        for pat in b["patterns"]:
            cur.execute(
                """
                SELECT item_id FROM couche_b.procurement_dict_items
                WHERE LOWER(label_fr) LIKE %s AND active = TRUE
                LIMIT 1
                """,
                (f"%{pat.lower()}%",),
            )
            ir = cur.fetchone()
            if ir:
                try:
                    cur.execute(
                        """
                        INSERT INTO public.market_basket_items
                            (basket_id, item_id, default_quantity)
                        VALUES (%s, %s, 1.0)
                        ON CONFLICT DO NOTHING
                        """,
                        (bid, ir["item_id"]),
                    )
                except Exception as e:
                    print(f"  ERR basket_item {pat} : {e}")
                    basket_item_errors += 1

    conn.commit()
    card = len(items) * len(zones)
    if basket_item_errors > 0:
        print(f"WARN : {basket_item_errors} erreurs basket_items")
    print(
        f"items={items_ok} zones={zones_ok} "
        f"baskets={baskets_ok}/3 "
        f"basket_item_errors={basket_item_errors} "
        f"cardinalite={card}"
    )
    conn.close()
    sys.exit(0)


if __name__ == "__main__":
    main()

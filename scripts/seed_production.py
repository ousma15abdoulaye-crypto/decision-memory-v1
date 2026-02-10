#!/usr/bin/env python3
"""Seed script: idempotent insert of reference data (units, geo Mali, vendors, items).

Requires DATABASE_URL env var (sync or async driver accepted — script uses sync).
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

UNITS = [
    ("KG", "Kilogramme"),
    ("T", "Tonne"),
    ("L", "Litre"),
    ("M", "Mètre"),
    ("M2", "Mètre carré"),
    ("M3", "Mètre cube"),
    ("U", "Unité"),
    ("FORFAIT", "Forfait"),
    ("LOT", "Lot"),
]

GEO_COUNTRY = ("Mali", "country", None)

GEO_REGIONS = [
    "Bamako",
    "Kayes",
    "Koulikoro",
    "Sikasso",
    "Ségou",
    "Mopti",
    "Tombouctou",
    "Gao",
]

VENDORS = [
    ("SOMAGEP-SA", "Mali"),
    ("EDM-SA", "Mali"),
    ("Orange Mali", "Mali"),
]

ITEMS = [
    ("Ciment CPA 45", "Construction", "T"),
    ("Fer à béton HA 10", "Construction", "KG"),
    ("Gasoil", "Carburant", "L"),
    ("Ordinateur portable", "IT", "U"),
    ("Papier A4 (rame)", "Fourniture", "U"),
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Seed helpers (idempotent via INSERT … WHERE NOT EXISTS)
# ---------------------------------------------------------------------------

def seed_units(session: Session) -> int:
    count = 0
    for code, label in UNITS:
        exists = session.execute(
            text("SELECT 1 FROM units WHERE code = :code"), {"code": code}
        ).first()
        if not exists:
            session.execute(
                text("INSERT INTO units (id, code, label, created_at) VALUES (:id, :code, :label, :ts)"),
                {"id": _uid(), "code": code, "label": label, "ts": _now()},
            )
            count += 1
    return count


def seed_geo(session: Session) -> int:
    count = 0
    name, geo_type, parent_id = GEO_COUNTRY
    row = session.execute(
        text("SELECT id FROM geo_master WHERE name = :name AND geo_type = :gt"),
        {"name": name, "gt": geo_type},
    ).first()
    if row:
        country_id = row[0]
    else:
        country_id = _uid()
        session.execute(
            text("INSERT INTO geo_master (id, name, geo_type, parent_id, created_at) VALUES (:id, :name, :gt, :pid, :ts)"),
            {"id": country_id, "name": name, "gt": geo_type, "pid": parent_id, "ts": _now()},
        )
        count += 1

    for region_name in GEO_REGIONS:
        exists = session.execute(
            text("SELECT 1 FROM geo_master WHERE name = :name AND geo_type = 'region'"),
            {"name": region_name},
        ).first()
        if not exists:
            session.execute(
                text("INSERT INTO geo_master (id, name, geo_type, parent_id, created_at) VALUES (:id, :name, :gt, :pid, :ts)"),
                {"id": _uid(), "name": region_name, "gt": "region", "pid": country_id, "ts": _now()},
            )
            count += 1
    return count


def seed_vendors(session: Session) -> int:
    count = 0
    for vname, country in VENDORS:
        exists = session.execute(
            text("SELECT 1 FROM vendors WHERE canonical_name = :cn"),
            {"cn": vname},
        ).first()
        if not exists:
            session.execute(
                text("INSERT INTO vendors (id, canonical_name, country, created_at) VALUES (:id, :cn, :c, :ts)"),
                {"id": _uid(), "cn": vname, "c": country, "ts": _now()},
            )
            count += 1
    return count


def seed_items(session: Session) -> int:
    count = 0
    for iname, category, unit_code in ITEMS:
        exists = session.execute(
            text("SELECT 1 FROM items WHERE canonical_name = :cn"),
            {"cn": iname},
        ).first()
        if not exists:
            unit_row = session.execute(
                text("SELECT id FROM units WHERE code = :code"),
                {"code": unit_code},
            ).first()
            unit_id = unit_row[0] if unit_row else None
            session.execute(
                text("INSERT INTO items (id, canonical_name, category, unit_id, created_at) VALUES (:id, :cn, :cat, :uid, :ts)"),
                {"id": _uid(), "cn": iname, "cat": category, "uid": unit_id, "ts": _now()},
            )
            count += 1
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("❌ DATABASE_URL not set")
        sys.exit(1)

    sync_url = db_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    print(f"Seeding database: {sync_url.split('@')[-1] if '@' in sync_url else sync_url}")

    engine = create_engine(sync_url)

    with Session(engine) as session:
        n_units = seed_units(session)
        n_geo = seed_geo(session)
        n_vendors = seed_vendors(session)
        n_items = seed_items(session)
        session.commit()

    # Verify counts
    with engine.connect() as conn:
        units_total = conn.execute(text("SELECT count(*) FROM units")).scalar()
        geo_total = conn.execute(text("SELECT count(*) FROM geo_master")).scalar()
        vendors_total = conn.execute(text("SELECT count(*) FROM vendors")).scalar()
        items_total = conn.execute(text("SELECT count(*) FROM items")).scalar()

    print(f"✅ Units:   {units_total} total ({n_units} inserted)")
    print(f"✅ Geo:     {geo_total} total ({n_geo} inserted)")
    print(f"✅ Vendors: {vendors_total} total ({n_vendors} inserted)")
    print(f"✅ Items:   {items_total} total ({n_items} inserted)")

    ok = True
    if geo_total < 8:
        print(f"⚠️  Expected ≥8 geo entries, got {geo_total}")
        ok = False
    if units_total < 9:
        print(f"⚠️  Expected ≥9 units, got {units_total}")
        ok = False
    if vendors_total < 3:
        print(f"⚠️  Expected ≥3 vendors, got {vendors_total}")
        ok = False
    if items_total < 5:
        print(f"⚠️  Expected ≥5 items, got {items_total}")
        ok = False

    engine.dispose()

    if ok:
        print("🎉 Seed PASSED")
    else:
        print("❌ Seed counts below threshold")
        sys.exit(1)


if __name__ == "__main__":
    main()

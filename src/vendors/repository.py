"""
Accès DB vendor_identities — psycopg pur, ADR-0003.

SQL paramétré uniquement. Zéro ORM.
Le vendor_id est généré ICI · en transaction · pas dans l'ETL.
"""

import hashlib

from src.db import db_fetchall, get_connection
from src.vendors.region_codes import build_vendor_id


def generate_fingerprint(name_normalized: str, region_code: str) -> str:
    """
    Fingerprint anti-doublon — stable · déterministe · reproductible.
    Même input → même fingerprint · toujours.
    """
    canonical = f"{name_normalized}|ML|{region_code}"
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def insert_vendor(
    name_raw: str,
    name_normalized: str,
    zone_raw: str | None,
    zone_normalized: str,
    region_code: str,
    category_raw: str | None,
    email: str | None,
    phone: str | None,
    email_verified: bool,
    source: str = "EXCEL_M4",
) -> str | None:
    """
    Insère un vendor et retourne son DMS_VENDOR_ID.
    Le vendor_id est généré ici · en transaction · pas dans l'ETL.

    Returns:
        str  : DMS_VENDOR_ID assigné si insertion réussie
        None : doublon détecté · skipped proprement
    """
    fingerprint = generate_fingerprint(name_normalized, region_code)

    with get_connection() as conn:
        # Vérification doublon
        conn.execute(
            "SELECT vendor_id FROM vendor_identities "
            "WHERE fingerprint = %(fp)s LIMIT 1",
            {"fp": fingerprint},
        )
        existing = conn.fetchone()
        if existing:
            return None  # doublon · skipped · pas une erreur

        # Prochain numéro de séquence pour cette région
        pattern = f"DMS-VND-{region_code}-%"
        conn.execute(
            "SELECT COALESCE(MAX("
            " CAST(SPLIT_PART(vendor_id, '-', 4) AS INTEGER)"
            "), 0) + 1 "
            "FROM vendor_identities "
            "WHERE vendor_id LIKE %(pattern)s",
            {"pattern": pattern},
        )
        seq_row = conn.fetchone()
        seq = int(seq_row[list(seq_row.keys())[0]]) if seq_row else 1

        vendor_id = build_vendor_id(region_code, seq)

        conn.execute(
            """
            INSERT INTO vendor_identities (
                vendor_id, fingerprint,
                name_raw, name_normalized,
                zone_raw, zone_normalized,
                region_code, category_raw,
                email, phone,
                email_verified, is_active, source
            ) VALUES (
                %(vendor_id)s, %(fingerprint)s,
                %(name_raw)s, %(name_normalized)s,
                %(zone_raw)s, %(zone_normalized)s,
                %(region_code)s, %(category_raw)s,
                %(email)s, %(phone)s,
                %(email_verified)s, TRUE, %(source)s
            )
            """,
            {
                "vendor_id": vendor_id,
                "fingerprint": fingerprint,
                "name_raw": name_raw,
                "name_normalized": name_normalized,
                "zone_raw": zone_raw,
                "zone_normalized": zone_normalized,
                "region_code": region_code,
                "category_raw": category_raw,
                "email": email,
                "phone": phone,
                "email_verified": email_verified,
                "source": source,
            },
        )
        return vendor_id


def get_vendor_by_id(vendor_id: str) -> dict | None:
    with get_connection() as conn:
        conn.execute(
            "SELECT * FROM vendor_identities WHERE vendor_id = %(vid)s",
            {"vid": vendor_id},
        )
        return conn.fetchone()


def list_vendors(
    region_code: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    with get_connection() as conn:
        sql = "SELECT * FROM vendor_identities WHERE is_active = TRUE"
        params: dict = {"limit": limit, "offset": offset}

        if region_code:
            sql += " AND region_code = %(region_code)s"
            params["region_code"] = region_code

        sql += " ORDER BY name_normalized LIMIT %(limit)s OFFSET %(offset)s"
        return db_fetchall(conn, sql, params)

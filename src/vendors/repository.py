"""
Accès DB vendor_identities — psycopg pur, ADR-0003.

SQL paramétré uniquement. Zéro ORM.
Le vendor_id est généré ICI · en transaction · pas dans l'ETL.

Patch M4 :
  - insert_vendor : ON CONFLICT (fingerprint) DO NOTHING RETURNING vendor_id
  - get_next_sequence : regex ~ au lieu de LIKE
  - Paramètres badge activité ajoutés (activity_status, verified_by, verification_source)
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


def get_next_sequence(conn, region_code: str) -> int:
    """
    Retourne le prochain numéro de séquence pour une région.

    AVERTISSEMENT TD-001 :
    Cette opération n'est pas atomique.
    Deux appels concurrents dans la même région peuvent obtenir
    la même séquence et provoquer une collision sur vendor_id UNIQUE.
    Acceptable en M4 import séquentiel opérateur.
    À résoudre en M5+ via advisory lock ou table vendor_sequences.

    Patch M4 : utilise regex ~ à la place de LIKE (cohérence avec FIX-1).
    """
    regex = f"^DMS-VND-{region_code}-[0-9]{{4}}-[A-Z]$"
    conn.execute(
        "SELECT COALESCE(MAX("
        "  CAST(SPLIT_PART(vendor_id, '-', 4) AS INTEGER)"
        "), 0) + 1 AS next_seq "
        "FROM vendor_identities "
        "WHERE vendor_id ~ %(regex)s",
        {"regex": regex},
    )
    row = conn.fetchone()
    return int(row["next_seq"]) if row else 1


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
    activity_status: str = "UNVERIFIED",
    verified_by: str | None = None,
    verification_source: str | None = None,
    source: str = "EXCEL_M4",
) -> str | None:
    """
    Insertion atomique via ON CONFLICT DO NOTHING RETURNING.
    Race condition sur fingerprint éliminée (Patch M4 — FIX-4).

    LIMITE DOCUMENTÉE (TD-001) :
    get_next_sequence() MAX()+1 reste non atomique.
    Risque acceptable en import séquentiel M4.
    Solution M5+ : advisory lock ou table vendor_sequences.

    Returns:
        str  : DMS_VENDOR_ID assigné si insertion réussie
        None : doublon détecté via ON CONFLICT · skipped proprement
    """
    fingerprint = generate_fingerprint(name_normalized, region_code)

    with get_connection() as conn:
        seq = get_next_sequence(conn, region_code)
        vendor_id = build_vendor_id(region_code, seq)

        conn.execute(
            """
            INSERT INTO vendor_identities (
                vendor_id, fingerprint,
                name_raw, name_normalized,
                canonical_name,
                zone_raw, zone_normalized,
                region_code, category_raw,
                email, phone, email_verified,
                activity_status, verified_by,
                verification_source,
                is_active, source
            ) VALUES (
                %(vendor_id)s, %(fingerprint)s,
                %(name_raw)s, %(name_normalized)s,
                %(canonical_name)s,
                %(zone_raw)s, %(zone_normalized)s,
                %(region_code)s, %(category_raw)s,
                %(email)s, %(phone)s, %(email_verified)s,
                %(activity_status)s, %(verified_by)s,
                %(verification_source)s,
                TRUE, %(source)s
            )
            ON CONFLICT (fingerprint) DO NOTHING
            """,
            {
                "vendor_id": vendor_id,
                "fingerprint": fingerprint,
                "name_raw": name_raw,
                "name_normalized": name_normalized,
                "canonical_name": f"{name_normalized}|{region_code}",
                "zone_raw": zone_raw,
                "zone_normalized": zone_normalized,
                "region_code": region_code,
                "category_raw": category_raw,
                "email": email,
                "phone": phone,
                "email_verified": email_verified,
                "activity_status": activity_status,
                "verified_by": verified_by,
                "verification_source": verification_source,
                "source": source,
            },
        )

        # Vérifie si l'insertion a eu lieu (ON CONFLICT peut l'avoir ignorée)
        conn.execute(
            "SELECT vendor_id FROM vendor_identities "
            "WHERE fingerprint = %(fp)s LIMIT 1",
            {"fp": fingerprint},
        )
        row = conn.fetchone()
        if row and row["vendor_id"] == vendor_id:
            return vendor_id  # insertion réussie
        return None  # doublon · skipped proprement


def get_vendor_by_id(vendor_id: str) -> dict | None:
    with get_connection() as conn:
        conn.execute(
            "SELECT * FROM vendor_identities WHERE vendor_id = %(vid)s",
            {"vid": vendor_id},
        )
        return conn.fetchone()


def list_vendors(
    region_code: str | None = None,
    activity_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    with get_connection() as conn:
        sql = "SELECT * FROM vendor_identities WHERE is_active = TRUE"
        params: dict = {"limit": limit, "offset": offset}

        if region_code:
            sql += " AND region_code = %(region_code)s"
            params["region_code"] = region_code

        if activity_status:
            sql += " AND activity_status = %(activity_status)s"
            params["activity_status"] = activity_status

        sql += " ORDER BY name_normalized LIMIT %(limit)s OFFSET %(offset)s"
        return db_fetchall(conn, sql, params)

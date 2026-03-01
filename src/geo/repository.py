"""
Repository géographique — SQL paramétré uniquement, zéro ORM.
Toutes les fonctions sont en lecture seule (SELECT).
"""

from __future__ import annotations

from src.db import db_fetchall, get_connection


def get_countries(active_only: bool = True) -> list[dict]:
    with get_connection() as conn:
        where = "WHERE is_active = TRUE" if active_only else ""
        return db_fetchall(
            conn,
            f"SELECT * FROM geo_countries {where} ORDER BY name_fr",
            {},
        )


def get_country_by_iso2(iso2: str) -> dict | None:
    with get_connection() as conn:
        conn.execute(
            "SELECT * FROM geo_countries WHERE iso2 = :iso2",
            {"iso2": iso2.upper()},
        )
        return conn.fetchone()


def get_regions_by_country(iso2: str, active_only: bool = True) -> list[dict]:
    with get_connection() as conn:
        where_active = "AND r.is_active = TRUE" if active_only else ""
        return db_fetchall(
            conn,
            f"""
            SELECT r.*
            FROM geo_regions r
            JOIN geo_countries c ON c.id = r.country_id
            WHERE c.iso2 = :iso2 {where_active}
            ORDER BY r.name_fr
            """,
            {"iso2": iso2.upper()},
        )


def get_cercles_by_region(region_id: str, active_only: bool = True) -> list[dict]:
    with get_connection() as conn:
        where_active = "AND is_active = TRUE" if active_only else ""
        return db_fetchall(
            conn,
            f"""
            SELECT * FROM geo_cercles
            WHERE region_id = :region_id {where_active}
            ORDER BY name_fr
            """,
            {"region_id": region_id},
        )


def get_communes_by_cercle(cercle_id: str, active_only: bool = True) -> list[dict]:
    with get_connection() as conn:
        where_active = "AND is_active = TRUE" if active_only else ""
        return db_fetchall(
            conn,
            f"""
            SELECT * FROM geo_communes
            WHERE cercle_id = :cercle_id {where_active}
            ORDER BY name_fr
            """,
            {"cercle_id": cercle_id},
        )


def search_communes(q: str, limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        return db_fetchall(
            conn,
            """
            SELECT * FROM geo_communes
            WHERE is_active = TRUE
              AND name_fr ILIKE :pattern
            ORDER BY name_fr
            LIMIT :limit
            """,
            {"pattern": f"%{q}%", "limit": limit},
        )


def get_zones(active_only: bool = True) -> list[dict]:
    with get_connection() as conn:
        where = "WHERE is_active = TRUE" if active_only else ""
        return db_fetchall(
            conn,
            f"SELECT * FROM geo_zones_operationnelles {where} ORDER BY name_fr",
            {},
        )


def get_communes_by_zone(zone_id: str) -> list[dict]:
    with get_connection() as conn:
        return db_fetchall(
            conn,
            """
            SELECT c.*
            FROM geo_communes c
            JOIN geo_zone_commune_mapping m ON m.commune_id = c.id
            WHERE m.zone_id = :zone_id
              AND m.valid_until IS NULL
              AND c.is_active = TRUE
            ORDER BY c.name_fr
            """,
            {"zone_id": zone_id},
        )

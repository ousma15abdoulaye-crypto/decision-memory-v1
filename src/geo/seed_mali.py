"""
Seed Mali — données réelles bornées.
M3 prouve le réel. M3 n'épuise pas le référentiel national.

Seed M3 = géographie Mali officielle uniquement :
  - pays Mali
  - 11 régions officielles
  - cercles critiques Mopti
  - communes minimales de preuve

NOTE : geo_zones_operationnelles existe au schéma en M3
mais n'est pas seedée à ce jalon.
Les données organisationnelles et leurs mappings
seront chargés dans un jalon ultérieur, hors M3.

NOTE : code_instat ici = code interne DMS provisoire pour seed minimal M3.
Les codes INSTAT officiels Mali ne sont pas encore intégrés à ce jalon
et seront traités dans un jalon de données plus riche ultérieur.
"""

from __future__ import annotations

MALI_COUNTRY: dict = {
    "iso2": "ML",
    "iso3": "MLI",
    "name_fr": "Mali",
    "name_en": "Mali",
}

MALI_REGIONS: list[dict] = [
    {"code": "ML-1", "name_fr": "Kayes", "capitale": "Kayes"},
    {"code": "ML-2", "name_fr": "Koulikoro", "capitale": "Koulikoro"},
    {"code": "ML-3", "name_fr": "Sikasso", "capitale": "Sikasso"},
    {"code": "ML-4", "name_fr": "Ségou", "capitale": "Ségou"},
    {"code": "ML-5", "name_fr": "Mopti", "capitale": "Mopti"},
    {"code": "ML-6", "name_fr": "Tombouctou", "capitale": "Tombouctou"},
    {"code": "ML-7", "name_fr": "Gao", "capitale": "Gao"},
    {"code": "ML-8", "name_fr": "Kidal", "capitale": "Kidal"},
    {"code": "ML-9", "name_fr": "Taoudénit", "capitale": "Taoudénit"},
    {"code": "ML-10", "name_fr": "Ménaka", "capitale": "Ménaka"},
    {"code": "ML-BA", "name_fr": "Bamako", "capitale": "Bamako"},
]

MOPTI_CERCLES: list[dict] = [
    {"code": "MOP-BAN", "name_fr": "Bandiagara", "capitale": "Bandiagara"},
    {"code": "MOP-BKS", "name_fr": "Bankass", "capitale": "Bankass"},
    {"code": "MOP-DJE", "name_fr": "Djenné", "capitale": "Djenné"},
    {"code": "MOP-DOU", "name_fr": "Douentza", "capitale": "Douentza"},
    {"code": "MOP-KOR", "name_fr": "Koro", "capitale": "Koro"},
    {"code": "MOP-MOP", "name_fr": "Mopti", "capitale": "Mopti"},
    {"code": "MOP-TEN", "name_fr": "Ténenkou", "capitale": "Ténenkou"},
    {"code": "MOP-YOU", "name_fr": "Youwarou", "capitale": "Youwarou"},
]

MOPTI_COMMUNES_MIN: list[dict] = [
    {
        "code_instat": "ML-MOP-MOP",
        "name_fr": "Mopti",
        "type_commune": "urbaine",
        "chef_lieu": "Mopti",
        "cercle_code": "MOP-MOP",
    },
    {
        "code_instat": "ML-MOP-SEV",
        "name_fr": "Sévaré",
        "type_commune": "urbaine",
        "chef_lieu": "Sévaré",
        "cercle_code": "MOP-MOP",
    },
    {
        "code_instat": "ML-MOP-KOR",
        "name_fr": "Koro",
        "type_commune": "urbaine",
        "chef_lieu": "Koro",
        "cercle_code": "MOP-KOR",
    },
    {
        "code_instat": "ML-MOP-BAN",
        "name_fr": "Bandiagara",
        "type_commune": "urbaine",
        "chef_lieu": "Bandiagara",
        "cercle_code": "MOP-BAN",
    },
]


def run_seed(conn) -> dict:
    """
    Insère le seed Mali dans la DB via une connexion psycopg v3 brute.
    Idempotent : ON CONFLICT DO NOTHING sur toutes les insertions.
    Paramètre conn : psycopg.Connection avec row_factory=dict_row.
    Retourne un dict avec les counts insérés.
    """
    counts: dict[str, int] = {}

    def _exec(sql: str, params: dict):
        return conn.execute(sql, params)

    # 1. Pays
    cur = _exec(
        """
        INSERT INTO geo_countries (iso2, iso3, name_fr, name_en)
        VALUES (%(iso2)s, %(iso3)s, %(name_fr)s, %(name_en)s)
        ON CONFLICT (iso2) DO NOTHING
        RETURNING id
        """,
        MALI_COUNTRY,
    )
    row = cur.fetchone()
    if row:
        country_id = str(row["id"])
    else:
        cur = _exec(
            "SELECT id FROM geo_countries WHERE iso2 = %(iso2)s",
            {"iso2": MALI_COUNTRY["iso2"]},
        )
        country_id = str(cur.fetchone()["id"])
    counts["countries"] = 1

    # 2. Régions
    region_ids: dict[str, str] = {}
    for reg in MALI_REGIONS:
        cur = _exec(
            """
            INSERT INTO geo_regions (country_id, code, name_fr, capitale)
            VALUES (%(country_id)s, %(code)s, %(name_fr)s, %(capitale)s)
            ON CONFLICT (country_id, code) DO NOTHING
            RETURNING id, code
            """,
            {**reg, "country_id": country_id},
        )
        row = cur.fetchone()
        if row:
            region_ids[row["code"]] = str(row["id"])
        else:
            cur = _exec(
                "SELECT id FROM geo_regions WHERE country_id = %(cid)s AND code = %(code)s",
                {"cid": country_id, "code": reg["code"]},
            )
            region_ids[reg["code"]] = str(cur.fetchone()["id"])
    counts["regions"] = len(MALI_REGIONS)

    # 3. Cercles Mopti
    mopti_id = region_ids["ML-5"]
    cercle_ids: dict[str, str] = {}
    for cer in MOPTI_CERCLES:
        cur = _exec(
            """
            INSERT INTO geo_cercles (region_id, code, name_fr, capitale)
            VALUES (%(region_id)s, %(code)s, %(name_fr)s, %(capitale)s)
            ON CONFLICT (region_id, code) DO NOTHING
            RETURNING id, code
            """,
            {**cer, "region_id": mopti_id},
        )
        row = cur.fetchone()
        if row:
            cercle_ids[row["code"]] = str(row["id"])
        else:
            cur = _exec(
                "SELECT id FROM geo_cercles WHERE region_id = %(rid)s AND code = %(code)s",
                {"rid": mopti_id, "code": cer["code"]},
            )
            cercle_ids[cer["code"]] = str(cur.fetchone()["id"])
    counts["cercles"] = len(MOPTI_CERCLES)

    # 4. Communes minimales
    for com in MOPTI_COMMUNES_MIN:
        cercle_id = cercle_ids[com["cercle_code"]]
        _exec(
            """
            INSERT INTO geo_communes
                (cercle_id, code_instat, name_fr, type_commune, chef_lieu)
            VALUES
                (%(cercle_id)s, %(code_instat)s, %(name_fr)s,
                 %(type_commune)s, %(chef_lieu)s)
            ON CONFLICT (code_instat) DO NOTHING
            """,
            {
                "cercle_id": cercle_id,
                "code_instat": com["code_instat"],
                "name_fr": com["name_fr"],
                "type_commune": com["type_commune"],
                "chef_lieu": com["chef_lieu"],
            },
        )
    counts["communes"] = len(MOPTI_COMMUNES_MIN)

    # geo_zones_operationnelles non seedée en M3 — voir NOTE en tête de fichier
    counts["zones"] = 0

    return counts

"""
Tests M11 — Signal Integrity & Zone Coverage (ADR-011)

Couverture :
  T1  14 zones DETTE-1 ont toutes un severity_level
  T2  zone-menaka-1 ipc_4_emergency + corridor Gao->Menaka
  T3  market_surveys non vide (DETTE-2)
  T4  decision_history contient CRITICAL/WATCH (DETTE-3)
  T5  seasonal_patterns > baseline M10B (DETTE-4)
  T6  Zero signal en zone sans severity post-compute
  T7  Signaux totaux > baseline M10B (578)
  T8  Signaux CRITICAL uniquement sur zones ipc_3+ / ipc_4+

Regles :
  - Tests Railway (DMS_ALLOW_RAILWAY=1 requis)
  - Pas de mock — psycopg reel, DB Railway reelle
"""
import os

import psycopg
import pytest
from psycopg.rows import dict_row

DB = (
    os.environ.get("RAILWAY_DATABASE_URL", "")
    or os.environ.get("DATABASE_URL", "")
)
ALLOW_RAILWAY = os.environ.get("DMS_ALLOW_RAILWAY", "0") == "1"
M11_SEEDED = os.environ.get("M11_SEEDED", "0") == "1"
BASELINE_M10B = 578
BASELINE_SP = 1786

ZONES_DETTE1 = [
    "zone-bougouni-1", "zone-koutiala-1", "zone-sikasso-1",
    "zone-dioila-1", "zone-koulikoro-1", "zone-kita-1",
    "zone-segou-1", "zone-san-1", "zone-nioro-1",
    "zone-mopti-1", "zone-bandiagara-1", "zone-nara-1",
    "zone-douentza-1", "zone-taoudeni-1",
]


def _normalize_url(url: str) -> str:
    """Normalisation robuste psycopg v3 — coherente avec probe_m11.py."""
    if not url:
        return url
    if "://" in url:
        scheme_part, rest = url.split("://", 1)
        base_scheme = scheme_part.split("+")[0]
        url = f"{base_scheme}://{rest}"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


@pytest.fixture(scope="module")
def conn():
    if not DB:
        pytest.skip("DATABASE_URL absente")
    if not M11_SEEDED:
        pytest.skip(
            "M11_SEEDED=1 requis — seeds M11 non confirmes. "
            "Executer les scripts seed_* et compute_* avant les tests."
        )
    if "rlwy.net" in DB.lower() or "railway" in DB.lower():
        if not ALLOW_RAILWAY:
            pytest.skip("Railway detecte — set DMS_ALLOW_RAILWAY=1")
    normalized = _normalize_url(DB)
    c = psycopg.connect(normalized, row_factory=dict_row)
    yield c
    c.close()


def test_14_zones_ont_severity_level(conn):
    """Les 14 zones DETTE-1 ont un severity_level dans zone_context_registry."""
    cur = conn.cursor()
    manquantes = []
    for zone_id in ZONES_DETTE1:
        cur.execute("""
            SELECT severity_level
            FROM zone_context_registry
            WHERE zone_id = %s AND valid_until IS NULL
        """, (zone_id,))
        r = cur.fetchone()
        if not r or not r["severity_level"]:
            manquantes.append(zone_id)
    assert not manquantes, f"{len(manquantes)} zones sans severity_level : {manquantes}"


def test_menaka_zone_et_corridor(conn):
    """zone-menaka-1 ipc_4_emergency et corridor Gao->Menaka present."""
    cur = conn.cursor()
    cur.execute("""
        SELECT severity_level, structural_markup_pct
        FROM zone_context_registry
        WHERE zone_id = 'zone-menaka-1' AND valid_until IS NULL
    """)
    r = cur.fetchone()
    assert r is not None, "zone-menaka-1 absent de zone_context_registry"
    assert r["severity_level"] == "ipc_4_emergency", f"severity incorrect : {r['severity_level']}"
    assert float(r["structural_markup_pct"]) == 32.0, (
        f"markup incorrect : {r['structural_markup_pct']}"
    )

    cur.execute("""
        SELECT transport_markup, route_type
        FROM geo_price_corridors
        WHERE zone_from = 'zone-gao-1'
        AND   zone_to   = 'zone-menaka-1'
    """)
    r = cur.fetchone()
    assert r is not None, "Corridor Gao->Menaka absent"
    assert float(r["transport_markup"]) == 1.45, f"markup incorrect : {r['transport_markup']}"
    assert r["route_type"] == "unpaved", f"route_type incorrect : {r['route_type']}"


def test_market_surveys_non_vide(conn):
    """market_surveys contient des donnees proxy."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM market_surveys")
    r = cur.fetchone()
    assert r["n"] > 0, "market_surveys vide — seed DETTE-2 non applique"


def test_decision_history_non_vide(conn):
    """decision_history contient les signaux CRITICAL/WATCH."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM decision_history")
    r = cur.fetchone()
    assert r["n"] > 0, "decision_history vide — seed DETTE-3 non applique"


def test_seasonal_patterns_superieurs_baseline(conn):
    """seasonal_patterns >= 1786 apres completion."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM seasonal_patterns")
    r = cur.fetchone()
    assert r["n"] >= BASELINE_SP, f"seasonal_patterns ({r['n']}) < baseline M10B ({BASELINE_SP})"


def test_zero_signaux_zones_sans_severity(conn):
    """Aucun signal en zone sans zone_context_registry apres compute M11."""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) AS n
        FROM market_signals_v2 ms
        LEFT JOIN zone_context_registry zcr
          ON zcr.zone_id = ms.zone_id AND zcr.valid_until IS NULL
        WHERE zcr.zone_id IS NULL
    """)
    r = cur.fetchone()
    assert r["n"] == 0, f"{r['n']} signaux en zones non mappees"


def test_signaux_superieurs_baseline_m10b(conn):
    """Signaux post-compute M11 > 578."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM market_signals_v2")
    r = cur.fetchone()
    assert r["n"] > BASELINE_M10B, f"Signaux ({r['n']}) <= baseline ({BASELINE_M10B})"


def test_critical_uniquement_sur_zones_crise(conn):
    """Signaux CRITICAL uniquement sur zones ipc_3_crisis ou ipc_4_emergency."""
    cur = conn.cursor()
    cur.execute("""
        SELECT ms.zone_id, ms.alert_level, zcr.severity_level
        FROM market_signals_v2 ms
        JOIN zone_context_registry zcr
          ON zcr.zone_id = ms.zone_id AND zcr.valid_until IS NULL
        WHERE ms.alert_level = 'CRITICAL'
        AND   zcr.severity_level NOT IN ('ipc_3_crisis', 'ipc_4_emergency')
    """)
    incoh = cur.fetchall()
    assert not incoh, (
        f"{len(incoh)} signaux CRITICAL sur zones non-critiques : "
        f"{[(r['zone_id'], r['severity_level']) for r in incoh]}"
    )

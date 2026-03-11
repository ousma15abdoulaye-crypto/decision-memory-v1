"""
Tests invariants M8 — enterprise grade.
Usage : pytest tests/test_m8_invariants.py -v

Schema reel confirme par probe ETAPE 0 :
  item_id     : TEXT  (couche_b.procurement_dict_items — cle existante)
  users.id    : INTEGER
  units.id    : INTEGER
  cases.id    : TEXT
  geo_master.id : VARCHAR(50)
"""

import os
import subprocess

import psycopg
import pytest
from psycopg.rows import dict_row

try:
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

DB = os.environ.get("DATABASE_URL", "").replace(
    "postgresql+psycopg://", "postgresql://"
)


@pytest.fixture(scope="module")
def conn():
    if not DB:
        pytest.skip("DATABASE_URL absent -- tests DB ignores")
    c = psycopg.connect(DB, row_factory=dict_row)
    yield c
    c.close()


# ── Pre-conditions ────────────────────────────────────────────────────────────


def test_database_url_not_railway():
    assert "railway" not in DB.lower(), "CONTRACT-02 : DATABASE_URL contient railway"


def test_alembic_single_head():
    r = subprocess.run(
        ["alembic", "heads"],
        capture_output=True,
        text=True,
    )
    lines = [line for line in r.stdout.strip().splitlines() if line.strip()]
    assert len(lines) == 1, f"alembic heads != 1 : {lines}"


# ── Tables presentes ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "table",
    [
        "tracked_market_items",
        "tracked_market_zones",
        "market_baskets",
        "market_basket_items",
        "zone_context_registry",
        "zone_context_audit",
        "seasonal_patterns",
        "geo_price_corridors",
        "survey_campaigns",
        "survey_campaign_items",
        "survey_campaign_zones",
        "market_surveys",
        "price_anomaly_alerts",
    ],
)
def test_table_exists(conn, table):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
    )
    assert cur.fetchone()["n"] == 1, f"Table manquante : {table}"


def test_market_coverage_matview_exists(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) AS n FROM pg_matviews WHERE matviewname = 'market_coverage'"
    )
    assert cur.fetchone()["n"] == 1


# ── Schema market_surveys ─────────────────────────────────────────────────────


def test_item_id_column_exists_in_surveys(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'market_surveys'
          AND column_name  = 'item_id'
        """,
    )
    assert cur.fetchone()["n"] == 1, "item_id absent de market_surveys"


def test_no_item_uid_column_in_surveys(conn):
    """item_uid ne doit pas exister dans market_surveys — seul item_id."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'market_surveys'
          AND column_name  = 'item_uid'
        """,
    )
    assert (
        cur.fetchone()["n"] == 0
    ), "item_uid present dans market_surveys -- doit etre item_id"


def test_no_is_bidirectional_in_corridors(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'geo_price_corridors'
          AND column_name  = 'is_bidirectional'
        """,
    )
    assert cur.fetchone()["n"] == 0, "is_bidirectional present -- interdit M8"


def test_no_org_id_in_market_baskets(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'market_baskets'
          AND column_name  = 'org_id'
        """,
    )
    assert (
        cur.fetchone()["n"] == 0
    ), "org_id dans market_baskets -- GLOBAL_CORE interdit"


def test_seasonal_patterns_unique_on_taxo_l3(conn):
    """Index UNIQUE explicite sur taxo_l3 (CREATE UNIQUE INDEX)."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS n FROM pg_indexes
        WHERE tablename  = 'seasonal_patterns'
          AND schemaname = 'public'
          AND indexdef ILIKE 'CREATE UNIQUE INDEX%'
          AND indexdef ILIKE '%taxo_l3%'
        """,
    )
    assert cur.fetchone()["n"] >= 1, "Index UNIQUE sur taxo_l3 manquant"


def test_source_case_id_is_text(conn):
    """source_case_id doit etre TEXT (cases.id = TEXT)."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'price_anomaly_alerts'
          AND column_name  = 'source_case_id'
        """,
    )
    r = cur.fetchone()
    assert r is not None, "source_case_id absent de price_anomaly_alerts"
    assert r["data_type"] in (
        "text",
        "character varying",
    ), f"source_case_id type incorrect : {r['data_type']}"


# ── Tables absentes (hors scope) ──────────────────────────────────────────────


MIGRATION_SKIP_FROM = "043"


def test_no_market_signals_created_by_m8(conn):
    """
    M8 ne doit pas avoir cree market_signals.
    On verifie que alembic_version = 042_market_surveys (head M8).
    Skip si head >= 043 (M9 applique).
    """
    cur = conn.cursor()
    cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
    r = cur.fetchone()
    assert r is not None, "alembic_version vide"
    ver = r["version_num"]
    try:
        prefix = str(ver).split("_")[0] if ver else ""
        current_num = int(prefix) if prefix.isdigit() else 0
    except (ValueError, TypeError):
        current_num = 0
    try:
        skip_from = int(MIGRATION_SKIP_FROM.split("_")[0])
    except (ValueError, IndexError):
        skip_from = 43
    if current_num >= skip_from:
        pytest.skip(
            f"Migration {ver} >= {MIGRATION_SKIP_FROM} — test M8 skippé"
        )
    assert ver == "042_market_surveys", f"head inattendu : {ver}"


def test_no_price_series_view(conn):
    """
    M8 ne cree pas price_series (hors scope M8).
    Skip si head >= 043 (M9 cree price_series).
    """
    cur = conn.cursor()
    cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
    r = cur.fetchone()
    ver = r.get("version_num") if r else None
    try:
        prefix = str(ver).split("_")[0] if ver else ""
        current_num = int(prefix) if prefix.isdigit() else 0
    except (ValueError, TypeError):
        current_num = 0
    try:
        skip_from = int(MIGRATION_SKIP_FROM.split("_")[0])
    except (ValueError, IndexError):
        skip_from = 43
    if current_num >= skip_from:
        pytest.skip(
            f"Migration {ver} >= {MIGRATION_SKIP_FROM} — price_series attendue"
        )
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM information_schema.views
        WHERE table_name = 'price_series'
        """,
    )
    assert cur.fetchone()["n"] == 0, "price_series creee -- hors scope M8"


def test_no_refresh_trigger_on_surveys(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM information_schema.triggers
        WHERE event_object_table = 'market_surveys'
          AND trigger_name LIKE '%coverage_refresh%'
        """,
    )
    assert cur.fetchone()["n"] == 0, "trigger refresh synchrone -- interdit"


# ── Triggers presents ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "trigger,table",
    [
        ("trg_compute_price_per_unit", "market_surveys"),
        ("trg_zone_context_no_overlap", "zone_context_registry"),
        ("trg_zone_context_audit_log", "zone_context_registry"),
        ("trg_zone_context_audit_append_only", "zone_context_audit"),
        ("trg_market_survey_immutable_validated", "market_surveys"),
        ("trg_market_survey_flag_duplicate", "market_surveys"),
    ],
)
def test_trigger_exists(conn, trigger, table):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM information_schema.triggers
        WHERE trigger_schema     = 'public'
          AND trigger_name       = %s
          AND event_object_table = %s
        """,
        (trigger, table),
    )
    assert cur.fetchone()["n"] >= 1, f"Trigger manquant : {trigger} sur {table}"


# ── Contraintes CHECK enforced ────────────────────────────────────────────────


def test_price_quoted_positive_enforced(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT item_id FROM couche_b.procurement_dict_items"
        " WHERE active = TRUE LIMIT 1"
    )
    r = cur.fetchone()
    if not r:
        pytest.skip("dict_items vide")
    iid = r["item_id"]
    cur.execute("SELECT id FROM public.geo_master WHERE level = 2 LIMIT 1")
    r = cur.fetchone()
    if not r:
        pytest.skip("geo_master level=2 vide")
    zid = r["id"]
    with pytest.raises(Exception):
        cur.execute(
            """
            INSERT INTO public.market_surveys
                (item_id, price_quoted, supplier_raw, zone_id, date_surveyed)
            VALUES (%s, -1, 'test', %s, CURRENT_DATE)
            """,
            (iid, zid),
        )
    conn.rollback()


def test_collection_method_mercuriale_rejected(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT item_id FROM couche_b.procurement_dict_items"
        " WHERE active = TRUE LIMIT 1"
    )
    r = cur.fetchone()
    if not r:
        pytest.skip("dict_items vide")
    iid = r["item_id"]
    cur.execute("SELECT id FROM public.geo_master WHERE level = 2 LIMIT 1")
    r = cur.fetchone()
    if not r:
        pytest.skip("geo_master level=2 vide")
    zid = r["id"]
    with pytest.raises(Exception):
        cur.execute(
            """
            INSERT INTO public.market_surveys (
                item_id, price_quoted, supplier_raw,
                zone_id, date_surveyed, collection_method
            ) VALUES (%s, 100, 'test', %s, CURRENT_DATE, 'mercuriale')
            """,
            (iid, zid),
        )
    conn.rollback()


def test_zone_context_overlap_rejected(conn):
    cur = conn.cursor()
    cur.execute("SELECT id FROM public.geo_master WHERE level = 2 LIMIT 1")
    r = cur.fetchone()
    if not r:
        pytest.skip("geo_master level=2 vide")
    zid = r["id"]
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM public.zone_context_registry
        WHERE zone_id = %s AND valid_until IS NULL
        """,
        (zid,),
    )
    if cur.fetchone()["n"] == 0:
        pytest.skip("Aucun contexte actif pour tester overlap")
    with pytest.raises(Exception):
        cur.execute(
            """
            INSERT INTO public.zone_context_registry (
                zone_id, context_type, severity_level,
                structural_markup_pct, valid_from, source
            ) VALUES (%s, 'normal', 'ipc_1_minimal', 0, CURRENT_DATE, 'test')
            """,
            (zid,),
        )
    conn.rollback()


def test_zone_context_audit_append_only(conn):
    cur = conn.cursor()
    cur.execute("SELECT id FROM public.zone_context_audit LIMIT 1")
    r = cur.fetchone()
    if not r:
        pytest.skip("zone_context_audit vide")
    with pytest.raises(Exception):
        cur.execute(
            "DELETE FROM public.zone_context_audit WHERE id = %s",
            (r["id"],),
        )
    conn.rollback()


def test_basket_type_humanitarian_nfi_valid(conn):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO public.market_baskets (name, description, basket_type)
        VALUES ('_test_nfi', 'test', 'humanitarian_nfi')
        ON CONFLICT (name) DO NOTHING
        """)
    conn.rollback()


def test_basket_type_construction_valid(conn):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO public.market_baskets (name, description, basket_type)
        VALUES ('_test_const', 'test', 'construction_materials')
        ON CONFLICT (name) DO NOTHING
        """)
    conn.rollback()


def test_basket_type_invalid_rejected(conn):
    cur = conn.cursor()
    with pytest.raises(Exception):
        cur.execute("""
            INSERT INTO public.market_baskets (name, description, basket_type)
            VALUES ('_test_bad', 'test', 'humanitarian_reference')
            """)
    conn.rollback()


# ── market_coverage bornee scope tracked ─────────────────────────────────────


def test_market_coverage_uses_tracked_scope(conn):
    """
    market_coverage doit partir de tracked_market_items.
    CROSS JOIN borne : tracked_market_zones uniquement.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT definition FROM pg_matviews WHERE matviewname = 'market_coverage'"
    )
    r = cur.fetchone()
    assert r is not None
    defn = r["definition"].lower()
    assert (
        "tracked_market_items" in defn
    ), "market_coverage ne passe pas par tracked_market_items"
    assert (
        "cross join" not in defn or "tracked_market_zones" in defn
    ), "market_coverage CROSS JOIN non borne detecte"


# ── Types FK corrects ─────────────────────────────────────────────────────────


def test_created_by_type_in_zone_context_registry(conn):
    """created_by doit etre INTEGER (users.id = INTEGER)."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'zone_context_registry'
          AND column_name  = 'created_by'
        """,
    )
    r = cur.fetchone()
    assert r is not None, "Colonne created_by absente de zone_context_registry"
    assert (
        r["data_type"] == "integer"
    ), f"created_by type = {r['data_type']} -- attendu integer"


def test_unit_id_type_in_market_surveys(conn):
    """unit_id doit etre INTEGER (units.id = INTEGER)."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'market_surveys'
          AND column_name  = 'unit_id'
        """,
    )
    r = cur.fetchone()
    assert r is not None, "Colonne unit_id absente de market_surveys"
    assert (
        r["data_type"] == "integer"
    ), f"unit_id type = {r['data_type']} -- attendu integer"

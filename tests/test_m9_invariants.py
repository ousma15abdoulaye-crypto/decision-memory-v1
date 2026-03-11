"""
Tests invariants M9 -- Market Signal Engine V1.1.
pytest tests/test_m9_invariants.py -v
"""

import os
import sys

import psycopg
import pytest
from psycopg.rows import dict_row

sys.path.insert(0, ".")

try:
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

from src.couche_a.market.formula_v11 import (
    ALERT_THRESHOLDS,
    FORMULA_VERSION,
    FRESHNESS,
    IQR_MULTIPLIER,
    WEIGHTS,
    ContextSnapshot,
    FormulaV11,
    PricePoint,
)

DB = os.environ.get("DATABASE_URL", "").replace(
    "postgresql+psycopg://", "postgresql://"
)

F = FormulaV11()


@pytest.fixture(scope="module")
def conn():
    if not DB:
        pytest.skip("DATABASE_URL absent -- tests DB ignores")
    c = psycopg.connect(DB, row_factory=dict_row)
    yield c
    c.close()


# ── Constantes ADR figees ─────────────────────────────────────────────────────


class TestConstantesADR:
    def test_formula_version(self):
        assert FORMULA_VERSION == "1.1"

    def test_poids_mercuriale(self):
        assert WEIGHTS["mercuriale_official"] == 0.50

    def test_poids_survey(self):
        assert WEIGHTS["market_survey"] == 0.35

    def test_poids_decision(self):
        assert WEIGHTS["decision_history"] == 0.15

    def test_poids_somme_1(self):
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

    def test_freshness_0(self):
        assert FRESHNESS[0] == 1.00

    def test_freshness_1(self):
        assert FRESHNESS[1] == 0.90

    def test_freshness_2(self):
        assert FRESHNESS[2] == 0.75

    def test_freshness_3(self):
        assert FRESHNESS[3] == 0.55

    def test_iqr_multiplier(self):
        assert IQR_MULTIPLIER == 2.5

    def test_seuil_ipc4_critical(self):
        assert ALERT_THRESHOLDS["ipc_4_emergency"]["CRITICAL"] == 40.0

    def test_seuil_ipc3_warning(self):
        assert ALERT_THRESHOLDS["ipc_3_crisis"]["WARNING"] == 30.0

    def test_seuil_normal_critical(self):
        assert ALERT_THRESHOLDS["normal"]["CRITICAL"] == 30.0


# ── Vecteurs figures ADR ──────────────────────────────────────────────────────


class TestVecteursADR:
    def test_v1_normal_source_unique(self):
        r = F.compute(
            "i",
            "z",
            [PricePoint(10000.0, "mercuriale_official", 0)],
            ContextSnapshot(),
        )
        assert r.price_raw == 10000.0
        assert r.price_crisis_adj == 10000.0
        assert r.price_seasonal_adj == 10000.0
        assert r.residual_pct == 0.0
        assert r.alert_level == "NORMAL"
        assert r.formula_version == "1.1"

    def test_v2_ipc4_menaka(self):
        r = F.compute(
            "i",
            "z",
            [PricePoint(22500.0, "mercuriale_official", 0)],
            ContextSnapshot(
                context_type="security_crisis",
                severity_level="ipc_4_emergency",
                structural_markup_pct=32.0,
                seasonal_deviation_pct=8.0,
            ),
        )
        assert r.price_raw == 22500.0
        assert r.price_crisis_adj is not None
        assert abs(r.price_crisis_adj - 17045.45) < 0.1
        assert r.price_seasonal_adj is not None
        assert abs(r.price_seasonal_adj - 15782.82) < 0.1
        assert r.residual_pct is not None
        assert abs(r.residual_pct - 42.56) < 0.5
        assert r.alert_level == "CRITICAL"

    def test_v3_multi_sources_freshness(self):
        pts = [
            PricePoint(10000.0, "mercuriale_official", 0),
            PricePoint(11000.0, "market_survey", 2),
            PricePoint(9500.0, "decision_history", 1),
        ]
        r = F.compute("i", "z", pts, ContextSnapshot())
        num = 0.50 * 1.00 * 10000 + 0.35 * 0.75 * 11000 + 0.15 * 0.90 * 9500
        den = 0.50 * 1.00 + 0.35 * 0.75 + 0.15 * 0.90
        expected = round(num / den, 2)
        assert r.price_raw is not None
        assert abs(r.price_raw - expected) < 0.1
        assert r.residual_pct == 0.0
        assert r.alert_level == "NORMAL"

    def test_v4_ipc3_sous_seuil(self):
        r = F.compute(
            "i",
            "z",
            [PricePoint(15000.0, "mercuriale_official", 0)],
            ContextSnapshot(
                context_type="security_crisis",
                severity_level="ipc_3_crisis",
                structural_markup_pct=25.0,
                seasonal_deviation_pct=0.0,
            ),
        )
        assert r.alert_level == "CONTEXT_NORMAL"
        assert r.price_crisis_adj is not None
        assert abs(r.price_crisis_adj - 12000.0) < 0.1
        assert r.residual_pct is not None
        assert abs(r.residual_pct - 25.0) < 0.1

    def test_v5_normal_no_adjustment(self):
        r = F.compute(
            "i",
            "z",
            [PricePoint(12000.0, "mercuriale_official", 0)],
            ContextSnapshot(
                context_type="normal",
                severity_level="ipc_1_minimal",
                structural_markup_pct=0.0,
                seasonal_deviation_pct=0.0,
            ),
        )
        assert r.alert_level == "NORMAL"
        assert r.residual_pct == 0.0


# ── Tests unitaires ───────────────────────────────────────────────────────────


class TestUnitaires:
    def test_points_vides_retourne_empty(self):
        r = F.compute("i", "z", [], ContextSnapshot())
        assert r.signal_quality == "empty"
        assert r.price_raw is None

    def test_iqr_ejecte_outlier_massif(self):
        # 8 valeurs normales + 1 outlier massif
        # Avec suffisamment de points, IQR ejected l'outlier
        normals = [
            10000.0,
            10100.0,
            9900.0,
            10050.0,
            9950.0,
            10200.0,
            9800.0,
            10150.0,
        ]
        cleaned = F.reject_outliers(normals + [500_000.0])
        assert 500_000.0 not in cleaned
        assert len(cleaned) == len(normals)

    def test_freshness_age_0(self):
        assert F.freshness_factor(0) == 1.00

    def test_freshness_age_3(self):
        assert F.freshness_factor(3) == 0.55

    def test_freshness_age_vieux(self):
        assert F.freshness_factor(99) == 0.30

    def test_compte_sources(self):
        pts = [
            PricePoint(10000.0, "mercuriale_official", 0),
            PricePoint(10100.0, "mercuriale_official", 1),
            PricePoint(10200.0, "market_survey", 0),
        ]
        r = F.compute("i", "z", pts, ContextSnapshot())
        assert r.source_mercuriale_count == 2
        assert r.source_survey_count == 1
        assert r.source_decision_count == 0

    def test_propagation_marquee(self):
        r = F.compute(
            "i",
            "z",
            [PricePoint(10000.0, "mercuriale_official", 0)],
            ContextSnapshot(),
            propagated_from="zone-gao-1",
        )
        assert r.is_propagated is True
        assert r.propagated_from_zone == "zone-gao-1"
        assert r.signal_quality == "propagated"

    def test_auto_normalise_sans_decision_history(self):
        """Poids 0.15 inactif -> formule s'auto-normalise correctement."""
        pts_avec = [
            PricePoint(10000.0, "mercuriale_official", 0),
            PricePoint(10000.0, "decision_history", 0),
        ]
        pts_sans = [PricePoint(10000.0, "mercuriale_official", 0)]
        r_avec = F.compute("i", "z", pts_avec, ContextSnapshot())
        r_sans = F.compute("i", "z", pts_sans, ContextSnapshot())
        # Les deux donnent price_raw=10000 (meme prix)
        assert r_avec.price_raw == 10000.0
        assert r_sans.price_raw == 10000.0


# ── Tests DB ──────────────────────────────────────────────────────────────────


class TestDB:
    def test_signal_computation_log_existe(self, conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS n FROM information_schema.tables
            WHERE table_name = 'signal_computation_log'
              AND table_schema = 'public'
        """)
        assert cur.fetchone()["n"] == 1

    def test_market_signals_v2_existe(self, conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS n FROM information_schema.tables
            WHERE table_name = 'market_signals_v2'
              AND table_schema = 'public'
        """)
        assert cur.fetchone()["n"] == 1

    def test_market_signals_v2_unique(self, conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS n FROM pg_indexes
            WHERE tablename = 'market_signals_v2'
              AND indexdef LIKE '%item_id%zone_id%'
        """)
        assert cur.fetchone()["n"] >= 1

    def test_trigger_formula_immutable(self, conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS n FROM information_schema.triggers
            WHERE event_object_table = 'market_signals_v2'
              AND trigger_name =
                  'trg_market_signals_v2_formula_immutable'
        """)
        assert cur.fetchone()["n"] >= 1

    def test_vues_intelligence_existent(self, conn):
        cur = conn.cursor()
        for vue in ["price_series", "vendor_price_positioning", "basket_cost_by_zone"]:
            cur.execute(
                """
                SELECT COUNT(*) AS n FROM information_schema.views
                WHERE table_name = %s AND table_schema = 'public'
            """,
                (vue,),
            )
            assert cur.fetchone()["n"] == 1, f"Vue manquante : {vue}"

    def test_alembic_head_043(self, conn):
        cur = conn.cursor()
        cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
        r = cur.fetchone()
        assert r is not None
        assert (
            r["version_num"] == "043_market_signals_v11"
        ), f"head inattendu : {r['version_num']}"

    def test_market_signals_legacy_intact(self, conn):
        """market_signals legacy ne doit pas avoir ete modifie par M9."""
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS n FROM information_schema.tables
            WHERE table_name = 'market_signals'
              AND table_schema = 'public'
        """)
        assert cur.fetchone()["n"] == 1, "market_signals legacy disparue"

    def test_formula_version_immutable(self, conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT item_id, zone_id FROM public.market_signals_v2
            WHERE formula_version = '1.1' LIMIT 1
        """)
        r = cur.fetchone()
        if not r:
            pytest.skip("Aucun signal calcule encore")
        with pytest.raises(Exception) as exc:
            cur.execute(
                """
                UPDATE public.market_signals_v2
                SET formula_version = '9.9'
                WHERE item_id = %s AND zone_id = %s
            """,
                (r["item_id"], r["zone_id"]),
            )
        conn.rollback()
        assert any(
            kw in str(exc.value).lower()
            for kw in ["immuable", "immutable", "formula", "interdit"]
        )

    def test_instat_seasonal_patterns_confidence(self, conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS n FROM public.seasonal_patterns
            WHERE computation_version = 'v1.0_instat'
        """)
        n = cur.fetchone()["n"]
        if n > 0:
            cur.execute("""
                SELECT AVG(confidence) AS avg_conf
                FROM public.seasonal_patterns
                WHERE computation_version = 'v1.0_instat'
            """)
            r = cur.fetchone()
            assert float(r["avg_conf"]) >= 0.90

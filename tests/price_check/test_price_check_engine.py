"""
Tests -- PriceCheck Engine (DMS V3.3.2 / ADR-0009).

T1 : WITHIN_REF -- offre sous le seuil acceptable
T2 : ABOVE_REF -- offre moderement au-dessus (entre acceptable et eleve)
T3 : ABOVE_REF -- offre fortement au-dessus (> ratio_eleve)
T4 : NO_REF -- alias UNRESOLVED (aucune normalisation)
T5 : NO_REF -- alias resolu mais aucune entree mercuriale
T6 : batch conserve l'ordre (3 offres)
T7 : batch appelle normalize_batch une seule fois (spy)
T8 : fallback hardcode trace si scoring_configs vide
T9 : prix_total_soumis = prix_unitaire * quantite
T10: verdict NO_REF si mercuriale vide pour item connu

Seed explicite : couche_b.mercuriale_raw_queue + public.scoring_configs.
Cleanup : DELETE WHERE source = 't-pricecheck-*' / profile_code='TEST_PROFILE'.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from src.couche_a.price_check.engine import analyze, analyze_batch
from src.couche_a.price_check.schemas import OffreInput, PriceVerdict

_SOURCE_TAG = "t-pricecheck-pytest"

_ITEM_ID_KNOWN = "gasoil"  # real item in couche_b.procurement_dict_items
_ITEM_ID_ABSENT = "DICT_TEST_PC_ABSENT_999"  # does not exist in dict
_PROFILE_TEST = "TEST_PROFILE"

_SEED_SCORING = """
    INSERT INTO public.scoring_configs (
        id, profile_code, commercial_formula, commercial_weight,
        capacity_formula, capacity_weight,
        sustainability_formula, sustainability_weight,
        essentials_weight, price_ratio_acceptable, price_ratio_eleve,
        created_at, updated_at
    )
    VALUES (
        'scoring_test_profile', %s, 'price_lowest_100', 0.5,
        'capacity_experience', 0.3,
        'sustainability_certifications', 0.1,
        0.0, 1.05, 1.20,
        '2026-02-22T00:00:00Z', '2026-02-22T00:00:00Z'
    )
    ON CONFLICT (id) DO NOTHING;
"""

_SEED_MERCURIALE = """
    INSERT INTO couche_b.mercuriale_raw_queue
        (id, raw_line, source, parse_status, item_id,
         price_min, price_avg, price_max, currency, parse_errors)
    VALUES
        (gen_random_uuid(), 'test seed line', %s, 'ok', %s,
         900.0, 1000.0, 1100.0, 'XOF', '[]'::jsonb)
    ON CONFLICT DO NOTHING;
"""

_DEL_SCORING = "DELETE FROM public.scoring_configs WHERE profile_code = %s;"
_DEL_MERCURIALE = "DELETE FROM couche_b.mercuriale_raw_queue WHERE source = %s;"


@pytest.fixture()
def seeded_conn(db_conn):
    """Fixture: seed TEST_PROFILE in scoring_configs + 1 mercuriale entry."""
    with db_conn.cursor() as cur:
        cur.execute(_SEED_SCORING, (_PROFILE_TEST,))
        cur.execute(_SEED_MERCURIALE, (_SOURCE_TAG, _ITEM_ID_KNOWN))
    db_conn.commit()
    yield db_conn
    with db_conn.cursor() as cur:
        cur.execute(_DEL_SCORING, (_PROFILE_TEST,))
        cur.execute(_DEL_MERCURIALE, (_SOURCE_TAG,))
    db_conn.commit()


def _mock_norm(item_id: str | None):
    """Helper: build a mock NormalisationResult-like object."""

    class _FakeNorm:
        def __init__(self, iid):
            self.item_id = iid
            self.score = 1.0 if iid else 0.0
            self.strategy = "exact" if iid else "unresolved"
            self.input_raw = "test"
            self.normalized_input = "test"

    return _FakeNorm(item_id)


class TestAnalyzeSingle:
    def test_t1_within_ref(self, seeded_conn):
        """T1: prix_total <= prix_ref * 1.05 -> WITHIN_REF."""
        offre = OffreInput(
            alias_raw="gasoil litre test",
            prix_unitaire=1000.0,
            quantite=1.0,
            profile_code=_PROFILE_TEST,
        )
        with patch("src.couche_a.price_check.engine.normalize_batch") as mock_nb:
            mock_nb.return_value = [_mock_norm(_ITEM_ID_KNOWN)]
            result = analyze(offre, seeded_conn)

        assert result.verdict == PriceVerdict.WITHIN_REF
        assert result.prix_ref == 1000.0
        assert result.ratio == pytest.approx(1.0, rel=1e-4)
        assert result.item_id == _ITEM_ID_KNOWN

    def test_t2_above_ref_moderement(self, seeded_conn):
        """T2: ratio entre 1.05 et 1.20 -> ABOVE_REF, note moderately."""
        offre = OffreInput(
            alias_raw="gasoil litre test",
            prix_unitaire=1100.0,
            quantite=1.0,
            profile_code=_PROFILE_TEST,
        )
        with patch("src.couche_a.price_check.engine.normalize_batch") as mock_nb:
            mock_nb.return_value = [_mock_norm(_ITEM_ID_KNOWN)]
            result = analyze(offre, seeded_conn)

        assert result.verdict == PriceVerdict.ABOVE_REF
        assert result.ratio == pytest.approx(1.10, rel=1e-3)
        assert any("moderately" in n for n in result.notes)

    def test_t3_above_ref_fortement(self, seeded_conn):
        """T3: ratio > 1.20 -> ABOVE_REF, note significantly."""
        offre = OffreInput(
            alias_raw="gasoil litre test",
            prix_unitaire=1300.0,
            quantite=1.0,
            profile_code=_PROFILE_TEST,
        )
        with patch("src.couche_a.price_check.engine.normalize_batch") as mock_nb:
            mock_nb.return_value = [_mock_norm(_ITEM_ID_KNOWN)]
            result = analyze(offre, seeded_conn)

        assert result.verdict == PriceVerdict.ABOVE_REF
        assert result.ratio == pytest.approx(1.30, rel=1e-3)
        assert any("significantly" in n for n in result.notes)

    def test_t4_no_ref_unresolved(self, seeded_conn):
        """T4: alias UNRESOLVED (item_id=None) -> NO_REF."""
        offre = OffreInput(
            alias_raw="xyz inconnu absurde 9999",
            prix_unitaire=500.0,
            profile_code=_PROFILE_TEST,
        )
        with patch("src.couche_a.price_check.engine.normalize_batch") as mock_nb:
            mock_nb.return_value = [_mock_norm(None)]
            result = analyze(offre, seeded_conn)

        assert result.verdict == PriceVerdict.NO_REF
        assert result.prix_ref is None
        assert result.ratio is None
        assert any("UNRESOLVED" in n for n in result.notes)

    def test_t5_no_ref_absent_mercuriale(self, seeded_conn):
        """T5: alias resolu mais item_id absent de mercuriale -> NO_REF."""
        offre = OffreInput(
            alias_raw="item absent mercuriale",
            prix_unitaire=500.0,
            profile_code=_PROFILE_TEST,
        )
        with patch("src.couche_a.price_check.engine.normalize_batch") as mock_nb:
            mock_nb.return_value = [_mock_norm(_ITEM_ID_ABSENT)]
            result = analyze(offre, seeded_conn)

        assert result.verdict == PriceVerdict.NO_REF
        assert result.prix_ref is None
        assert result.item_id == _ITEM_ID_ABSENT


class TestAnalyzeBatch:
    def test_t6_batch_ordre_preserve(self, seeded_conn):
        """T6: batch de 3 offres -- l'ordre est conserve."""
        offres = [
            OffreInput(alias_raw="a", prix_unitaire=1000.0, profile_code=_PROFILE_TEST),
            OffreInput(alias_raw="b", prix_unitaire=500.0, profile_code=_PROFILE_TEST),
            OffreInput(alias_raw="c", prix_unitaire=1300.0, profile_code=_PROFILE_TEST),
        ]
        norms = [
            _mock_norm(_ITEM_ID_KNOWN),
            _mock_norm(None),
            _mock_norm(_ITEM_ID_KNOWN),
        ]
        with patch("src.couche_a.price_check.engine.normalize_batch") as mock_nb:
            mock_nb.return_value = norms
            results = analyze_batch(offres, seeded_conn)

        assert len(results) == 3
        assert results[0].alias_raw == "a"
        assert results[1].alias_raw == "b"
        assert results[2].alias_raw == "c"

    def test_t7_batch_normalize_batch_une_fois(self, seeded_conn):
        """T7: normalize_batch appele une seule fois pour tout le batch."""
        offres = [
            OffreInput(alias_raw="a", prix_unitaire=100.0, profile_code=_PROFILE_TEST),
            OffreInput(alias_raw="b", prix_unitaire=200.0, profile_code=_PROFILE_TEST),
            OffreInput(alias_raw="c", prix_unitaire=300.0, profile_code=_PROFILE_TEST),
        ]
        with patch("src.couche_a.price_check.engine.normalize_batch") as mock_nb:
            mock_nb.return_value = [_mock_norm(None)] * 3
            analyze_batch(offres, seeded_conn)
            assert (
                mock_nb.call_count == 1
            ), f"normalize_batch appele {mock_nb.call_count} fois (attendu: 1)"

    def test_t9_prix_total_soumis(self, seeded_conn):
        """T9: prix_total_soumis = prix_unitaire * quantite."""
        offre = OffreInput(
            alias_raw="test quantite",
            prix_unitaire=500.0,
            quantite=3.0,
            profile_code=_PROFILE_TEST,
        )
        with patch("src.couche_a.price_check.engine.normalize_batch") as mock_nb:
            mock_nb.return_value = [_mock_norm(None)]
            result = analyze(offre, seeded_conn)

        assert result.prix_total_soumis == pytest.approx(1500.0)


class TestFallback:
    def test_t8_fallback_trace_si_scoring_configs_vide(self, db_conn):
        """T8: note 'fallback hardcoded' tracee si scoring_configs vide (mock)."""
        offre = OffreInput(
            alias_raw="test fallback",
            prix_unitaire=1000.0,
            profile_code=f"PROFILE_INEXISTANT_{uuid.uuid4().hex[:8]}",
        )
        with patch("src.couche_a.price_check.engine.normalize_batch") as mock_nb:
            mock_nb.return_value = [_mock_norm(None)]
            with patch(
                "src.couche_a.price_check.engine._get_thresholds",
                return_value=(1.05, 1.20),
            ):
                with patch(
                    "src.couche_a.price_check.engine._get_mercuriale_prices",
                    return_value={},
                ):
                    # Simulate empty scoring_configs count
                    class _FakeCur:
                        def __enter__(self):
                            return self

                        def __exit__(self, *a):
                            pass

                        def execute(self, *a, **kw):
                            pass

                        def fetchone(self):
                            return {"n": 0}

                    class _FakeConn:
                        def cursor(self):
                            return _FakeCur()

                    result = analyze(offre, _FakeConn())  # type: ignore[arg-type]

        assert result.verdict == PriceVerdict.NO_REF
        assert any("fallback hardcoded" in n for n in result.notes)

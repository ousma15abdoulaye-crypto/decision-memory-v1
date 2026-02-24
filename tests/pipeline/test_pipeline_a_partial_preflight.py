# tests/pipeline/test_pipeline_a_partial_preflight.py
"""
L9 — Préflight pipeline A/partial.

Prouve les 4 reason_codes exacts du step preflight (INV-P préflight uniquement) :
  CASE_NOT_FOUND        → blocked
  DAO_MISSING           → blocked
  OFFERS_MISSING        → blocked
  MIN_OFFERS_INSUFFICIENT → blocked
  cas minimal valide    → ok

Prouve que step.meta contient dao_present et offers_count exacts.
"""

from __future__ import annotations

import uuid

from src.couche_a.pipeline.service import (
    RC_CASE_NOT_FOUND,
    RC_DAO_MISSING,
    RC_MIN_OFFERS_INSUFFICIENT,
    RC_OFFERS_MISSING,
    _preflight_case_a_partial,
)

# ---------------------------------------------------------------------------
# CASE_NOT_FOUND → blocked
# ---------------------------------------------------------------------------


def test_preflight_case_not_found_returns_blocked(db_conn):
    """CASE_NOT_FOUND : case_id inexistant → status=blocked + reason_code exact."""
    case_id = f"ghost-{uuid.uuid4()}"
    outcome = _preflight_case_a_partial(case_id, db_conn)

    assert outcome.status == "blocked", f"Attendu blocked, obtenu {outcome.status!r}"
    assert (
        outcome.reason_code == RC_CASE_NOT_FOUND
    ), f"Attendu {RC_CASE_NOT_FOUND!r}, obtenu {outcome.reason_code!r}"
    assert outcome.meta["dao_present"] is False
    assert outcome.meta["offers_count"] == 0


# ---------------------------------------------------------------------------
# DAO_MISSING → blocked
# ---------------------------------------------------------------------------


def test_preflight_dao_missing_returns_blocked(db_conn, case_factory):
    """DAO_MISSING : case existe, aucun critère DAO → status=blocked."""
    case_id = case_factory()
    outcome = _preflight_case_a_partial(case_id, db_conn)

    assert outcome.status == "blocked", f"Attendu blocked, obtenu {outcome.status!r}"
    assert (
        outcome.reason_code == RC_DAO_MISSING
    ), f"Attendu {RC_DAO_MISSING!r}, obtenu {outcome.reason_code!r}"
    assert outcome.meta["dao_present"] is False
    assert outcome.meta["offers_count"] == 0


# ---------------------------------------------------------------------------
# OFFERS_MISSING → blocked
# ---------------------------------------------------------------------------


def test_preflight_offers_missing_returns_blocked(db_conn, case_factory):
    """OFFERS_MISSING : case + DAO présents, aucune offre → status=blocked."""
    case_id = case_factory()
    crit_id = str(uuid.uuid4())

    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.dao_criteria
                (id, case_id, categorie, critere_nom, description,
                 ponderation, type_reponse, seuil_elimination,
                 ordre_affichage, created_at)
            VALUES (%s, %s, 'commercial', 'Prix', 'Prix unitaire',
                    1.0, 'quantitatif', NULL, 0, NOW()::text)
            """,
            (crit_id, case_id),
        )

    try:
        outcome = _preflight_case_a_partial(case_id, db_conn)

        assert (
            outcome.status == "blocked"
        ), f"Attendu blocked, obtenu {outcome.status!r}"
        assert (
            outcome.reason_code == RC_OFFERS_MISSING
        ), f"Attendu {RC_OFFERS_MISSING!r}, obtenu {outcome.reason_code!r}"
        assert outcome.meta["dao_present"] is True
        assert outcome.meta["offers_count"] == 0
    finally:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM public.dao_criteria WHERE id = %s", (crit_id,))


# ---------------------------------------------------------------------------
# MIN_OFFERS_INSUFFICIENT → blocked
# ---------------------------------------------------------------------------


def test_preflight_min_offers_insufficient_returns_blocked(db_conn, case_factory):
    """MIN_OFFERS_INSUFFICIENT : 1 seule offre (< 2 requis) → status=blocked."""
    case_id = case_factory()
    crit_id = str(uuid.uuid4())
    offer_id = str(uuid.uuid4())

    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.dao_criteria
                (id, case_id, categorie, critere_nom, description,
                 ponderation, type_reponse, seuil_elimination,
                 ordre_affichage, created_at)
            VALUES (%s, %s, 'commercial', 'Prix', 'Prix unitaire',
                    1.0, 'quantitatif', NULL, 0, NOW()::text)
            """,
            (crit_id, case_id),
        )
        cur.execute(
            """
            INSERT INTO public.offers
                (id, case_id, supplier_name, offer_type,
                 file_hash, submitted_at, created_at)
            VALUES (%s, %s, 'Fournisseur-Unique', 'financial',
                    'hash-abc123', NOW()::text, NOW()::text)
            """,
            (offer_id, case_id),
        )

    try:
        outcome = _preflight_case_a_partial(case_id, db_conn)

        assert (
            outcome.status == "blocked"
        ), f"Attendu blocked, obtenu {outcome.status!r}"
        assert (
            outcome.reason_code == RC_MIN_OFFERS_INSUFFICIENT
        ), f"Attendu {RC_MIN_OFFERS_INSUFFICIENT!r}, obtenu {outcome.reason_code!r}"
        assert outcome.meta["dao_present"] is True
        assert outcome.meta["offers_count"] == 1
    finally:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM public.dao_criteria WHERE id = %s", (crit_id,))
            cur.execute("DELETE FROM public.offers WHERE id = %s", (offer_id,))


# ---------------------------------------------------------------------------
# Cas minimal valide → ok
# ---------------------------------------------------------------------------


def test_preflight_valid_case_returns_ok(db_conn, pipeline_case_with_dao_and_offers):
    """Cas minimal valide (DAO + 2 offres) → status=ok, meta exact."""
    case_id = pipeline_case_with_dao_and_offers
    outcome = _preflight_case_a_partial(case_id, db_conn)

    assert outcome.status == "ok", (
        f"Attendu ok, obtenu {outcome.status!r} "
        f"(reason_code={outcome.reason_code!r})"
    )
    assert outcome.reason_code is None
    assert outcome.meta["dao_present"] is True
    assert outcome.meta["offers_count"] >= 2


# ---------------------------------------------------------------------------
# meta contient dao_present et offers_count exacts
# ---------------------------------------------------------------------------


def test_preflight_meta_contains_exact_dao_present_and_offers_count(
    db_conn, pipeline_case_with_dao_and_offers
):
    """meta contient dao_present=True et offers_count exact (V2.2)."""
    case_id = pipeline_case_with_dao_and_offers
    outcome = _preflight_case_a_partial(case_id, db_conn)

    assert "dao_present" in outcome.meta, "meta doit contenir 'dao_present'"
    assert "offers_count" in outcome.meta, "meta doit contenir 'offers_count'"
    assert outcome.meta["dao_present"] is True
    assert isinstance(outcome.meta["offers_count"], int)
    assert outcome.meta["offers_count"] == 2

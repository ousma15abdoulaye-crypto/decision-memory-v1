"""
Tests L4 -- M-PARSING-MERCURIALE -- DMS V3.3.2

T1  : parse ligne simple -> ok + min/avg/max corrects
T2  : nombres avec espaces "70 000 73 833 84 000" -> float correct
T3  : nombres avec virgule "1 250,50 1 300,00 1 400,00" -> float correct
T4  : designation multi-ligne concatenee (2 seg + ligne prix) -> ok
T5  : inconnu -> normalisation UNRESOLVED score=0 status partiel ou ok
T6  : raw_line intacte (PARSE-001)
T7  : batch conserve l'ordre
T8  : batch appelle normalize_batch une seule fois (spy/mock)
T9  : entree "|||" -> unparseable + parse_errors non vide
T10 : prix presents mais unite absente -> partial + "unit missing"
T11 : persist=true -> INSERT verifie en DB (raw_line, prix, currency, parse_errors)
T12 : persist=true + unparseable -> parse_errors non vide en DB

psycopg v3 -- row_factory=dict_row -- conftest.db_conn.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest

from src.api.routers.mercuriale import _persist
from src.couche_b.mercuriale.parser import parse_batch, parse_line
from src.couche_b.mercuriale.schemas import ParseStatus
from src.couche_b.normalisation.schemas import NormalisationResult, NormStrategy

# ---------------------------------------------------------------------------
# Helper : NormalisationResult UNRESOLVED factice (pour mocks)
# ---------------------------------------------------------------------------


def _unresolved(alias: str) -> NormalisationResult:
    return NormalisationResult(
        input_raw=alias,
        normalized_input=alias,
        item_id=None,
        strategy=NormStrategy.UNRESOLVED,
        score=0.0,
        confidence_note=None,
    )


# ---------------------------------------------------------------------------
# T1 -- ligne simple ok
# ---------------------------------------------------------------------------


def test_t1_parse_simple_line_ok():
    """T1 : parse_line standard -> ok, min/avg/max corrects."""
    line = "Agenda Simple Unite 2 500 3 300 4 000"
    draft = parse_line(line)
    assert draft.status == ParseStatus.OK
    assert draft.price_min == pytest.approx(2500.0)
    assert draft.price_avg == pytest.approx(3300.0)
    assert draft.price_max == pytest.approx(4000.0)


# ---------------------------------------------------------------------------
# T2 -- nombres avec espaces separateurs de milliers
# ---------------------------------------------------------------------------


def test_t2_amounts_with_space_separators():
    """T2 : '70 000 73 833 84 000' -> floats corrects."""
    line = "Abonnement journal Annee 70 000 73 833 84 000"
    draft = parse_line(line)
    assert draft.price_min == pytest.approx(70000.0)
    assert draft.price_avg == pytest.approx(73833.0)
    assert draft.price_max == pytest.approx(84000.0)


# ---------------------------------------------------------------------------
# T3 -- virgule decimale
# ---------------------------------------------------------------------------


def test_t3_amounts_with_comma_decimal():
    """T3 : '1 250,50 1 300,00 1 400,00' -> 1250.5 etc."""
    line = "Stylo Bic Piece 1 250,50 1 300,00 1 400,00"
    draft = parse_line(line)
    assert draft.price_min == pytest.approx(1250.50)
    assert draft.price_avg == pytest.approx(1300.00)
    assert draft.price_max == pytest.approx(1400.00)


# ---------------------------------------------------------------------------
# T4 -- designation multi-ligne (PARSE-006)
# ---------------------------------------------------------------------------


def test_t4_multiline_designation_batch(db_conn):
    """T4 : 2 segments designation + ligne prix -> designation concatenee, ok."""
    lines = [
        "Abonnement au journal ESSOR",
        "Abonnement annuel",
        "Abonnement annuel 70 000 73 833 84 000",
    ]
    with patch(
        "src.couche_b.mercuriale.parser.normalize_batch",
        return_value=[_unresolved("Abonnement au journal ESSOR Abonnement annuel")],
    ):
        results = parse_batch(lines, db_conn)

    assert len(results) == 1
    result = results[0]
    assert result.status == ParseStatus.OK
    assert "Abonnement au journal ESSOR" in result.designation_raw
    assert result.price_min == pytest.approx(70000.0)
    assert result.price_avg == pytest.approx(73833.0)
    assert result.price_max == pytest.approx(84000.0)


# ---------------------------------------------------------------------------
# T5 -- inconnu -> UNRESOLVED score=0
# ---------------------------------------------------------------------------


def test_t5_unknown_alias_unresolved(db_conn):
    """T5 : alias inconnu -> normalisation UNRESOLVED, score=0, item_id None."""
    line = "XYZ_PRODUIT_INEXISTANT_9999 Unite 500 600 700"
    results = parse_batch([line], db_conn)
    assert len(results) == 1
    result = results[0]
    norm = result.normalisation
    assert norm is not None, "normalisation ne doit jamais etre None"
    assert norm.item_id is None
    assert norm.score == pytest.approx(0.0)
    assert str(norm.strategy) == "unresolved"


# ---------------------------------------------------------------------------
# T6 -- raw_line intacte (PARSE-001)
# ---------------------------------------------------------------------------


def test_t6_raw_line_preserved():
    """T6 : raw_line doit etre conservee telle quelle (PARSE-001)."""
    line = "  Papier A4 Rame  500 600 700  "
    draft = parse_line(line)
    assert draft.raw_line == line, "raw_line ne doit pas etre modifiee"


# ---------------------------------------------------------------------------
# T7 -- batch conserve l'ordre
# ---------------------------------------------------------------------------


def test_t7_batch_preserves_order(db_conn):
    """T7 : l'ordre des resultats correspond a l'ordre des lignes d'entree."""
    lines = [
        "Crayon HB Piece 100 150 200",
        "Stylo rouge Piece 200 250 300",
        "Gomme Piece 50 75 100",
    ]
    with patch(
        "src.couche_b.mercuriale.parser.normalize_batch",
        return_value=[_unresolved(d) for d in ["Crayon HB", "Stylo rouge", "Gomme"]],
    ):
        results = parse_batch(lines, db_conn)

    assert len(results) == 3
    assert results[0].price_min == pytest.approx(100.0)
    assert results[1].price_min == pytest.approx(200.0)
    assert results[2].price_min == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# T8 -- normalize_batch appelee une seule fois (PARSE-005)
# ---------------------------------------------------------------------------


def test_t8_normalize_batch_called_once(db_conn):
    """T8 : parse_batch appelle normalize_batch exactement une fois (PARSE-005)."""
    lines = [
        "Article A Piece 100 200 300",
        "Article B Piece 400 500 600",
        "Article C Piece 700 800 900",
    ]
    mock_results = [_unresolved(d) for d in ["Article A", "Article B", "Article C"]]

    with patch(
        "src.couche_b.mercuriale.parser.normalize_batch",
        return_value=mock_results,
    ) as mock_nb:
        parse_batch(lines, db_conn)

    assert (
        mock_nb.call_count == 1
    ), f"normalize_batch appelee {mock_nb.call_count} fois au lieu de 1 (PARSE-005)"


# ---------------------------------------------------------------------------
# T9 -- decoratif "|||" -> unparseable
# ---------------------------------------------------------------------------


def test_t9_decorative_line_unparseable():
    """T9 : '|||' -> unparseable + parse_errors non vide."""
    draft = parse_line("|||")
    assert draft.status == ParseStatus.UNPARSEABLE
    assert len(draft.parse_errors) > 0


# ---------------------------------------------------------------------------
# T10 -- prix presents, unite absente -> partial + "unit missing"
# ---------------------------------------------------------------------------


def test_t10_prices_without_unit_partial():
    """T10 : 3 prix presents mais unite absente -> partial + 'unit missing'."""
    # Ligne sans texte avant les prix (pas d'unite extractable)
    line = "70 000 73 833 84 000"
    draft = parse_line(line)
    assert draft.status == ParseStatus.PARTIAL
    assert any(
        "unit missing" in e for e in draft.parse_errors
    ), f"'unit missing' attendu dans parse_errors, obtenu: {draft.parse_errors}"


# ---------------------------------------------------------------------------
# T11 -- persist=true -> INSERT verifie en DB
# ---------------------------------------------------------------------------

_SELECT_RAW_QUEUE = """
    SELECT raw_line, parse_status, price_min, price_avg, price_max,
           currency, parse_errors
    FROM couche_b.mercuriale_raw_queue
    WHERE source = %s
    ORDER BY imported_at DESC
    LIMIT 1
"""
_DELETE_RAW_QUEUE = "DELETE FROM couche_b.mercuriale_raw_queue WHERE source = %s"


def _decode_errors(val) -> list:
    """Normalise parse_errors : psycopg v3 retourne list ou str selon driver."""
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return json.loads(val)
    return []


def test_t11_persist_inserts_to_db(db_conn):
    """T11 : _persist() ecrit dans couche_b.mercuriale_raw_queue.

    Verifie : raw_line, parse_status, prix min/avg/max, currency, parse_errors vide.
    Cleanup strict en finally (anti-pollution CI).
    """
    source_ref = f"t11-{uuid.uuid4()}"
    results = parse_batch(["gasoil litre 625 650 675"], db_conn, source=source_ref)
    try:
        _persist(db_conn, results, source_ref)

        with db_conn.cursor() as cur:
            cur.execute(_SELECT_RAW_QUEUE, (source_ref,))
            row = cur.fetchone()

        assert row is not None, "Aucun enregistrement insere dans mercuriale_raw_queue"
        assert "gasoil litre 625 650 675" in row["raw_line"]
        assert row["parse_status"] in (
            "ok",
            "partial",
        ), f"parse_status inattendu: {row['parse_status']}"
        assert float(row["price_min"]) == pytest.approx(625.0)
        assert float(row["price_avg"]) == pytest.approx(650.0)
        assert float(row["price_max"]) == pytest.approx(675.0)
        assert row["currency"] == "XOF"
        assert (
            _decode_errors(row["parse_errors"]) == []
        ), f"parse_errors attendu vide, obtenu: {row['parse_errors']}"
    finally:
        with db_conn.cursor() as cur:
            cur.execute(_DELETE_RAW_QUEUE, (source_ref,))


# ---------------------------------------------------------------------------
# T12 -- persist=true + unparseable -> parse_errors non vide en DB
# ---------------------------------------------------------------------------


def test_t13_empty_line_preserved_in_batch(db_conn):
    """T13 : ligne vide -> UNPARSEABLE + ordre 1:1 preserve (FIX B2).

    Prouve que les lignes vides ne sont pas perdues et apparaissent
    a leur position exacte dans la liste de resultats.
    """
    lines = ["gasoil litre 625 650 675", "", "ciment 17000 18000 19000"]
    results = parse_batch(lines, conn=db_conn, source="T13")
    assert len(results) == 3
    assert (
        results[1].raw_line == ""
    ), f"raw_line attendu '' (vide), obtenu: {repr(results[1].raw_line)}"
    assert (
        results[1].status == ParseStatus.UNPARSEABLE
    ), f"status attendu UNPARSEABLE, obtenu: {results[1].status}"
    assert "EMPTY_LINE" in " ".join(
        results[1].parse_errors
    ), f"'EMPTY_LINE' attendu dans parse_errors, obtenu: {results[1].parse_errors}"


def test_t12_persist_unparseable_errors_in_db(db_conn):
    """T12 : ligne unparseable persistee -> parse_errors non vide en DB.

    Prouve que les erreurs ne sont jamais silencieuses (PARSE-002).
    Cleanup strict en finally (anti-pollution CI).
    """
    source_ref = f"t12-{uuid.uuid4()}"
    results = parse_batch(["|||"], db_conn, source=source_ref)
    try:
        _persist(db_conn, results, source_ref)

        with db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT parse_status, parse_errors
                FROM couche_b.mercuriale_raw_queue
                WHERE source = %s
                ORDER BY imported_at DESC
                LIMIT 1
                """,
                (source_ref,),
            )
            row = cur.fetchone()

        assert row is not None, "Aucun enregistrement insere dans mercuriale_raw_queue"
        assert (
            row["parse_status"] == "unparseable"
        ), f"parse_status attendu 'unparseable', obtenu: {row['parse_status']}"
        errors = _decode_errors(row["parse_errors"])
        assert (
            len(errors) > 0
        ), f"parse_errors doit etre non vide pour une ligne unparseable, obtenu: {errors}"
    finally:
        with db_conn.cursor() as cur:
            cur.execute(_DELETE_RAW_QUEUE, (source_ref,))

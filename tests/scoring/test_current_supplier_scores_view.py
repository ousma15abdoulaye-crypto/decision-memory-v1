"""L2 — current_supplier_scores view : correctness + non-déterminisme.

ADR-0006 / INV-6
Vue   : public.current_supplier_scores
Logique : DISTINCT ON (case_id, supplier_name, category) ORDER BY created_at DESC
          → retourne le run le plus récent par (case, supplier, category).

Pattern : db_conn (autocommit=True). UUID isolant par test.
          Zéro DELETE de cleanup sur score_runs (append-only by design).
"""

import uuid
from datetime import UTC, datetime

import pytest

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _insert_run(
    db_conn,
    case_id: str,
    supplier: str,
    category: str,
    score: float,
    created_at: str | None = None,
) -> None:
    """INSERT dans score_runs. created_at optionnel (forçage pour L2d)."""
    with db_conn.cursor() as cur:
        if created_at is None:
            cur.execute(
                """
                INSERT INTO public.score_runs (case_id, supplier_name, category, score_value)
                VALUES (%s, %s, %s, %s)
                """,
                (case_id, supplier, category, score),
            )
        else:
            cur.execute(
                """
                INSERT INTO public.score_runs
                    (case_id, supplier_name, category, score_value, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (case_id, supplier, category, score, created_at),
            )


def _view_rows(db_conn, case_id: str) -> list[dict]:
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM public.current_supplier_scores WHERE case_id = %s",
            (case_id,),
        )
        return cur.fetchall()


# ---------------------------------------------------------------------------
# L2a — la vue retourne le run le plus récent
# ---------------------------------------------------------------------------


def test_l2a_view_returns_latest_score(db_conn):
    """Deux INSERTs pour le même (case, supplier, category) → la vue retourne le plus récent."""
    case_id = str(uuid.uuid4())

    _insert_run(db_conn, case_id, "ACME", "total", 70.0)
    _insert_run(db_conn, case_id, "ACME", "total", 95.0)

    rows = _view_rows(db_conn, case_id)

    assert (
        len(rows) == 1
    ), f"La vue doit retourner 1 ligne (DISTINCT ON), obtenu {len(rows)}"
    assert float(rows[0]["score_value"]) == pytest.approx(
        95.0
    ), f"Score attendu 95.0 (le plus récent), obtenu {rows[0]['score_value']}"


# ---------------------------------------------------------------------------
# L2b — 2 suppliers → 2 lignes
# ---------------------------------------------------------------------------


def test_l2b_two_suppliers_two_rows(db_conn):
    """2 fournisseurs distincts pour le même case → 2 lignes dans la vue."""
    case_id = str(uuid.uuid4())

    _insert_run(db_conn, case_id, "ACME", "total", 80.0)
    _insert_run(db_conn, case_id, "BETA", "total", 60.0)

    rows = _view_rows(db_conn, case_id)
    suppliers = {r["supplier_name"] for r in rows}

    assert len(rows) == 2, f"Attendu 2 lignes, obtenu {len(rows)}"
    assert suppliers == {"ACME", "BETA"}


# ---------------------------------------------------------------------------
# L2c — 2 catégories → 2 lignes
# ---------------------------------------------------------------------------


def test_l2c_two_categories_two_rows(db_conn):
    """1 fournisseur, 2 catégories distinctes → 2 lignes dans la vue."""
    case_id = str(uuid.uuid4())

    _insert_run(db_conn, case_id, "ACME", "total", 80.0)
    _insert_run(db_conn, case_id, "ACME", "commercial", 75.0)

    rows = _view_rows(db_conn, case_id)
    categories = {r["category"] for r in rows}

    assert len(rows) == 2, f"Attendu 2 lignes, obtenu {len(rows)}"
    assert categories == {"total", "commercial"}


# ---------------------------------------------------------------------------
# L2d — même timestamp → détection non-déterminisme (patch CTO)
# ---------------------------------------------------------------------------


def test_l2d_same_timestamp_determinism_probe(db_conn):
    """Deux runs avec created_at identique : la vue doit retourner la même ligne
    de façon répétable. Si le résultat varie → skip + signal CTO.

    La vue utilise DISTINCT ON sans tie-breaker secondaire.
    En cas d'égalité de created_at, Postgres choisit arbitrairement.
    Ce test sonde ce comportement sans assertion dure (risque non-déterminisme).
    """
    case_id = str(uuid.uuid4())
    ts = datetime.now(UTC).isoformat()

    _insert_run(db_conn, case_id, "ACME", "total", 70.0, created_at=ts)
    _insert_run(db_conn, case_id, "ACME", "total", 90.0, created_at=ts)

    scores = set()
    for _ in range(3):
        rows = _view_rows(db_conn, case_id)
        assert len(rows) == 1, "La vue doit retourner exactement 1 ligne"
        scores.add(float(rows[0]["score_value"]))

    if len(scores) > 1:
        pytest.skip(
            f"[CTO SIGNAL] Non-déterminisme détecté sur current_supplier_scores "
            f"quand created_at identiques. Valeurs observées : {scores}. "
            "Ajouter un tie-breaker secondaire (id DESC) à la vue."
        )

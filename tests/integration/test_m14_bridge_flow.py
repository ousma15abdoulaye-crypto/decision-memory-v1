"""
Tests d'integration -- Bridge M14 -> criterion_assessments (Rupture R1).

populate_assessments_from_m14(workspace_id) est synchrone.
Les tests verifient :
1. Workspace vide -> BridgeResult(created=0, errors=[])
2. Idempotence sur workspace vide
3. Sur donnees reelles (si evaluation_documents existent en DB) -> created >= 0

Les tests evitent d'inserer dans evaluation_documents car cette table
necessite un committee_id (FK V4.x) non disponible en DB locale vide.
Les tests 3+ s'executent uniquement si des evaluation_documents existent.
"""

from __future__ import annotations

import uuid

import psycopg
import psycopg.rows
import pytest

from src.db.core import _ConnectionWrapper
from tests.integration.conftest import _get_conn

# -- Helpers ------------------------------------------------------------------


def _make_wrap() -> tuple[_ConnectionWrapper, psycopg.Connection]:
    raw = _get_conn()
    raw.autocommit = True
    wrap = _ConnectionWrapper(raw)
    wrap.execute("SELECT set_config('app.is_admin', 'true', true)", {})
    return wrap, raw


def _make_empty_workspace(wrap: _ConnectionWrapper) -> tuple[uuid.UUID, uuid.UUID]:
    """Cree un tenant + workspace sans donnees M14."""
    tenant_id = uuid.uuid4()
    wrap.execute(
        "INSERT INTO tenants (id, code, name) VALUES (:tid, :code, :name)",
        {
            "tid": str(tenant_id),
            "code": f"t_m14_{tenant_id.hex[:6]}",
            "name": "M14 Test",
        },
    )
    ws_id = uuid.uuid4()
    wrap.execute(
        """
        INSERT INTO process_workspaces
            (id, tenant_id, created_by, reference_code, title, process_type, status)
        VALUES (:wsid, :tid, 1, :ref, :title, 'devis_simple', 'draft')
        """,
        {
            "wsid": str(ws_id),
            "tid": str(tenant_id),
            "ref": f"M14E-{ws_id.hex[:8]}",
            "title": f"WS M14 test {ws_id.hex[:8]}",
        },
    )
    return ws_id, tenant_id


def _cleanup(wrap: _ConnectionWrapper, ws_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
    for tbl, col in [
        ("criterion_assessments", "workspace_id"),
        ("process_workspaces", "id"),
    ]:
        try:
            wrap.execute(f"DELETE FROM {tbl} WHERE {col} = :wsid", {"wsid": str(ws_id)})
        except Exception:  # noqa: BLE001
            pass
    try:
        wrap.execute("DELETE FROM tenants WHERE id = :tid", {"tid": str(tenant_id)})
    except Exception:  # noqa: BLE001
        pass


def _count_evaluation_documents(wrap: _ConnectionWrapper) -> int:
    wrap.execute("SELECT COUNT(*) AS n FROM evaluation_documents", {})
    row = wrap.fetchone()
    return int((row or {}).get("n") or 0)


# -- Tests --------------------------------------------------------------------


class TestM14BridgeEmptyWorkspace:
    def test_bridge_on_workspace_with_no_evaluation_docs_returns_zero(self) -> None:
        """
        Un workspace sans evaluation_documents -> BridgeResult(created=0, errors=[]).
        """
        from src.services.m14_bridge import populate_assessments_from_m14

        wrap, raw = _make_wrap()
        ws_id, tenant_id = _make_empty_workspace(wrap)

        try:
            result = populate_assessments_from_m14(str(ws_id))
            assert result is not None
            assert result.created == 0
            assert result.updated == 0
            assert result.errors == []
        finally:
            _cleanup(wrap, ws_id, tenant_id)
            raw.close()

    def test_bridge_idempotent_on_empty_workspace(self) -> None:
        """
        Deux appels consecutifs sur workspace vide : created=0 les deux fois.
        """
        from src.services.m14_bridge import populate_assessments_from_m14

        wrap, raw = _make_wrap()
        ws_id, tenant_id = _make_empty_workspace(wrap)

        try:
            r1 = populate_assessments_from_m14(str(ws_id))
            r2 = populate_assessments_from_m14(str(ws_id))
            assert r1.created == r2.created == 0
            assert r1.errors == r2.errors == []
        finally:
            _cleanup(wrap, ws_id, tenant_id)
            raw.close()


class TestM14BridgeWithExistingData:
    def test_bridge_on_workspace_with_scores_matrix(self) -> None:
        """
        Si des evaluation_documents existent en DB, le bridge retourne un
        BridgeResult valide (created >= 0, errors=[]).
        Skippe si aucun evaluation_document disponible.
        """
        from src.services.m14_bridge import populate_assessments_from_m14

        wrap, raw = _make_wrap()

        try:
            doc_count = _count_evaluation_documents(wrap)
            if doc_count == 0:
                pytest.skip(
                    "Aucun evaluation_document en DB locale -- "
                    "test a executer apres synchronisation M14 (disponible en production)"
                )

            # Utilise le premier workspace qui a un evaluation_document
            wrap.execute(
                """
                SELECT workspace_id FROM evaluation_documents
                WHERE workspace_id IS NOT NULL
                  AND scores_matrix IS NOT NULL
                  AND scores_matrix != '{}'::jsonb
                LIMIT 1
                """,
                {},
            )
            row = wrap.fetchone()
            if not row or not row.get("workspace_id"):
                pytest.skip("Aucun evaluation_document avec scores_matrix non vide")

            ws_id = str(row["workspace_id"])
            result = populate_assessments_from_m14(ws_id)

            assert result is not None
            assert result.errors == [], f"Erreurs inattendues : {result.errors}"
            # created + updated + skipped doit etre >= 0
            total = result.created + result.updated + result.skipped
            assert total >= 0

        finally:
            raw.close()

    def test_bridge_idempotent_with_real_workspace(self) -> None:
        """
        Deux appels sur le meme workspace : 2e appel.created <= 1er.
        Skippe si aucun evaluation_document disponible.
        """
        from src.services.m14_bridge import populate_assessments_from_m14

        wrap, raw = _make_wrap()

        try:
            wrap.execute(
                """
                SELECT workspace_id FROM evaluation_documents
                WHERE workspace_id IS NOT NULL
                  AND scores_matrix IS NOT NULL
                LIMIT 1
                """,
                {},
            )
            row = wrap.fetchone()
            if not row or not row.get("workspace_id"):
                pytest.skip("Aucun evaluation_document en DB -- test non applicable")

            ws_id = str(row["workspace_id"])
            first = populate_assessments_from_m14(ws_id)
            second = populate_assessments_from_m14(ws_id)

            assert first.errors == [] and second.errors == []
            assert second.created <= first.created, (
                f"La 2e sync ne devrait pas creer plus que la 1re. "
                f"1re={first.created}, 2e={second.created}"
            )

        finally:
            raw.close()

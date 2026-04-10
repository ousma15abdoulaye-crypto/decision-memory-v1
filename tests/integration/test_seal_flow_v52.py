"""
Tests d'integration -- Flow de scellement V5.2 (run_all_seal_checks).

Verifie que :
- Quorum insuffisant -> SealCheckResult.passed = False avec erreur quorum
- Flags non resolus -> SealCheckResult.passed = False avec erreur flag
- Quorum OK + 0 flags -> SealCheckResult.passed = True

run_all_seal_checks est synchrone et utilise _ConnectionWrapper de src.db.core.
Tous les membres utilisent user_id=1 (admin, toujours existant en DB).
"""

from __future__ import annotations

import uuid

import psycopg
import psycopg.rows

from src.db.core import _ConnectionWrapper
from tests.integration.conftest import _get_conn

# -- Helpers ------------------------------------------------------------------


def _make_wrap() -> tuple[_ConnectionWrapper, psycopg.Connection]:
    """Cree un _ConnectionWrapper avec app.is_admin=true."""
    raw = _get_conn()
    raw.autocommit = True
    wrap = _ConnectionWrapper(raw)
    wrap.execute("SELECT set_config('app.is_admin', 'true', true)", {})
    return wrap, raw


def _make_tenant(wrap: _ConnectionWrapper) -> uuid.UUID:
    tid = uuid.uuid4()
    wrap.execute(
        "INSERT INTO tenants (id, code, name) VALUES (:tid, :code, :name)",
        {"tid": str(tid), "code": f"t_{tid.hex[:8]}", "name": f"Tenant {tid.hex[:8]}"},
    )
    return tid


def _make_workspace(wrap: _ConnectionWrapper, tenant_id: uuid.UUID) -> uuid.UUID:
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
            "ref": f"SEAL-{ws_id.hex[:8]}",
            "title": f"WS seal test {ws_id.hex[:8]}",
        },
    )
    return ws_id


def _add_member(
    wrap: _ConnectionWrapper,
    workspace_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: str,
) -> None:
    """Ajoute un membre avec user_id=1 (admin, FK valide) et le role specifie."""
    wrap.execute(
        """
        INSERT INTO workspace_memberships
            (id, workspace_id, tenant_id, user_id, role, granted_by, granted_at)
        VALUES (:mid, :wsid, :tid, 1, :role, 1, NOW())
        ON CONFLICT DO NOTHING
        """,
        {
            "mid": str(uuid.uuid4()),
            "wsid": str(workspace_id),
            "tid": str(tenant_id),
            "role": role,
        },
    )


def _add_open_flag(
    wrap: _ConnectionWrapper,
    workspace_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    wrap.execute(
        """
        INSERT INTO assessment_comments
            (id, workspace_id, tenant_id, author_user_id, content,
             comment_type, is_flag, resolved)
        VALUES (:cid, :wsid, :tid, 1, :content, 'flag', true, false)
        """,
        {
            "cid": str(uuid.uuid4()),
            "wsid": str(workspace_id),
            "tid": str(tenant_id),
            "content": "Flag de test non resolu",
        },
    )


def _cleanup(
    wrap: _ConnectionWrapper, workspace_id: uuid.UUID, tenant_id: uuid.UUID
) -> None:
    for tbl, col in [
        ("assessment_comments", "workspace_id"),
        ("workspace_memberships", "workspace_id"),
        ("process_workspaces", "id"),
    ]:
        try:
            wrap.execute(
                f"DELETE FROM {tbl} WHERE {col} = :wsid",
                {"wsid": str(workspace_id)},
            )
        except Exception:  # noqa: BLE001
            pass
    try:
        wrap.execute("DELETE FROM tenants WHERE id = :tid", {"tid": str(tenant_id)})
    except Exception:  # noqa: BLE001
        pass


# -- Tests --------------------------------------------------------------------


class TestSealChecksQuorum:
    def test_quorum_insufficient_blocks_seal(self) -> None:
        """2 membres < 4 minimum -> passed=False avec erreur quorum."""
        from src.services.seal_checks import run_all_seal_checks

        wrap, raw = _make_wrap()
        tenant_id = _make_tenant(wrap)
        ws_id = _make_workspace(wrap, tenant_id)

        _add_member(wrap, ws_id, tenant_id, "supply_chain")
        _add_member(wrap, ws_id, tenant_id, "finance")

        try:
            result = run_all_seal_checks(wrap, str(ws_id))
            assert not result.passed, "Quorum insuffisant devrait bloquer le seal"
            quorum_errors = [
                e
                for e in result.errors
                if "quorum" in e.lower() or "membre" in e.lower() or "4" in e
            ]
            assert quorum_errors, f"Pas d'erreur quorum dans : {result.errors}"
        finally:
            _cleanup(wrap, ws_id, tenant_id)
            raw.close()


class TestSealChecksFlags:
    def test_open_flag_blocks_seal(self) -> None:
        """4 membres (quorum OK) + 1 flag non resolu -> passed=False avec erreur flag."""
        from src.services.seal_checks import run_all_seal_checks

        wrap, raw = _make_wrap()
        tenant_id = _make_tenant(wrap)
        ws_id = _make_workspace(wrap, tenant_id)

        for role in ["supply_chain", "finance", "technical", "budget_holder"]:
            _add_member(wrap, ws_id, tenant_id, role)

        _add_open_flag(wrap, ws_id, tenant_id)

        try:
            result = run_all_seal_checks(wrap, str(ws_id))
            assert not result.passed, "Flag non resolu devrait bloquer le seal"
            flag_errors = [
                e for e in result.errors if "flag" in e.lower() or "signal" in e.lower()
            ]
            assert flag_errors, f"Pas d'erreur flag dans : {result.errors}"
        finally:
            _cleanup(wrap, ws_id, tenant_id)
            raw.close()


class TestSealChecksPass:
    def test_quorum_ok_no_flags_passes(self) -> None:
        """4 membres + 0 flags + dao_criteria vide (WARNING) -> passed=True."""
        from src.services.seal_checks import run_all_seal_checks

        wrap, raw = _make_wrap()
        tenant_id = _make_tenant(wrap)
        ws_id = _make_workspace(wrap, tenant_id)

        for role in ["supply_chain", "finance", "technical", "budget_holder"]:
            _add_member(wrap, ws_id, tenant_id, role)

        try:
            result = run_all_seal_checks(wrap, str(ws_id))
            assert result.passed, (
                f"Devrait passer (quorum OK, 0 flags).\n"
                f"Erreurs: {result.errors}\nWarnings: {result.warnings}"
            )
        finally:
            _cleanup(wrap, ws_id, tenant_id)
            raw.close()

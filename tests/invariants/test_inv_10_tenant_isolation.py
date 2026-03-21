"""Invariant 10 — isolation tenant (JWT tenant_id, cases API, SQL vs tables RLS 051).

- Garde-fous légers sur jwt_handler, UserClaims, auth cases.py.
- Scan statique des littéraux SQL (AST) : SELECT sur cases/criteria/supplier_scores/
  pipeline_runs sans indice de périmètre (tenant_id, case_id, org_id, owner_id, etc.).
- Table « vendors » : écarts documentés → avertissement (hors RLS 051), ex. liste
  is_active, recherche similarity.

La logique de scan vit dans inv10_tenant_sql_scan.py (un seul endroit).
"""

from __future__ import annotations

import inspect
from pathlib import Path

from tests.invariants.inv10_tenant_sql_scan import (
    scan_src_violations,
    warn_known_gaps,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CASES_API = REPO_ROOT / "src" / "api" / "cases.py"


def test_inv_10_jwt_emits_tenant_claim_parameter() -> None:
    """create_access_token accepte tenant_id (claim unique, pas org_id JWT)."""
    from src.couche_a.auth import jwt_handler

    sig = inspect.signature(jwt_handler.create_access_token)
    assert "tenant_id" in sig.parameters, (
        "create_access_token doit exposer tenant_id pour le contexte multi-tenant"
    )


def test_inv_10_user_claims_includes_tenant_id() -> None:
    from src.couche_a.auth.dependencies import UserClaims

    fields = getattr(UserClaims, "__annotations__", {})
    assert "tenant_id" in fields


def test_inv_10_cases_endpoints_depend_on_get_current_user() -> None:
    """Handlers cases sensibles : auth obligatoire."""
    text = CASES_API.read_text(encoding="utf-8")
    assert "get_current_user" in text
    assert "Depends(get_current_user)" in text
    assert "def create_case" in text
    assert "def list_cases" in text
    assert "def get_case" in text


def test_inv_10_list_cases_filters_by_tenant_and_owner_for_non_admin() -> None:
    """Non-admin : requête liste filtrée sur tenant_id et owner_id (aligné require_case_access)."""
    text = CASES_API.read_text(encoding="utf-8")
    assert "tenant_id" in text
    assert "owner_id" in text
    assert "WHERE tenant_id" in text or "tenant_id =" in text


def test_inv_10_selects_on_rls_tables_are_scoped_or_allowlisted() -> None:
    """Aucune régression : SELECT sur tables RLS sans filtre tenant / dossier / clé."""
    violations, gap_hits = scan_src_violations(REPO_ROOT)
    if gap_hits:
        warn_known_gaps(gap_hits)
    assert not violations, (
        "VIOLATION — SELECT sur table RLS (051) sans périmètre tenant/case/org/owner/id :\n"
        + "\n".join(
            f"  {v['file']}:{v['line']} [{v['table']}] {v['sql_preview']}"
            for v in violations
        )
    )

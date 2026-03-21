"""Invariant 10 — socle tenant (tenant_id), aligné arch-routing / migration 051.

La PR externe (Copilot) proposait org_id dans le JWT et des scans SQL lourds.
Ici : garde-fous légers cohérents avec le dépôt actuel (claim tenant_id, cases API).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CASES_API = REPO_ROOT / "src" / "api" / "cases.py"


def test_inv_10_jwt_emits_tenant_claim_parameter() -> None:
    """create_access_token accepte tenant_id (pas de divergence org_id JWT)."""
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
    """Les handlers cases critiques ne doivent pas être publics."""
    text = CASES_API.read_text(encoding="utf-8")
    assert "get_current_user" in text
    assert "Depends(get_current_user)" in text
    # create + list + get
    assert "def create_case" in text
    assert "def list_cases" in text
    assert "def get_case" in text


def test_inv_10_list_cases_filters_by_tenant_for_non_admin() -> None:
    """La liste non-admin doit filtrer sur tenant_id (aligné RLS / cases.tenant_id)."""
    text = CASES_API.read_text(encoding="utf-8")
    assert "tenant_id" in text
    assert "WHERE tenant_id" in text or "tenant_id =" in text

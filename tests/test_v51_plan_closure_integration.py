"""Fermeture plan V5.1 DevOps-grade — intégration ciblée (DB requise).

- O4 : GET membres sans JWT → 401.
- O4 bis : GET membres avec JWT sans ``matrix.read`` workspace → 403.
- O12 : POST /api/mql/stream persiste ``mql_query_log`` avec le **moteur MQL réel**
  (aucun mock de ``execute_mql_query`` — LLM absent de cette route).
- O9 : test ``test_seal_o9_alias_registered_on_main_app`` = **montage des chemins**
  uniquement. Dette E2 explicite : parité fonctionnelle ``committee/seal`` vs ``/seal``
  (même statut / cohérence ``seal_hash``) reste à couvrir avec TestClient + DB quand
  la fixture Postgres CI est stable.
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from main import app
from src.mql.templates import MQL_TEMPLATES


@pytest.fixture
def client() -> TestClient:
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    return TestClient(app)


def _admin_headers(c: TestClient) -> dict[str, str]:
    r = c.post(
        "/api/auth/login",
        json={"email": "admin", "password": "admin123"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_seal_o9_alias_registered_on_main_app() -> None:
    """Montage uniquement (Canon O9) — les deux chemins existent sur ``main:app``.

    Ne valide pas que les deux POST produisent le même comportement métier
    (statut, ``seal_hash``, etc.) ; voir docstring du module (dette E2).
    """
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/workspaces/{workspace_id}/committee/seal" in paths
    assert "/api/workspaces/{workspace_id}/seal" in paths


def test_list_workspace_members_requires_auth(client: TestClient) -> None:
    wid = str(uuid.uuid4())
    r = client.get(f"/api/workspaces/{wid}/members")
    assert r.status_code == 401


def test_list_workspace_members_requires_matrix_read(
    client: TestClient,
    workspace_factory,
) -> None:
    """Même tenant, utilisateur B sans ligne ``workspace_memberships`` sur ce WS → 403.

    Précondition explicite : en tant qu’admin, la liste des membres ne contient pas B.
    Si ``workspace_factory`` évolue pour créer un membership implicite, cette assertion
    échoue avant le scénario 403 (régression visible).
    """
    ws_id = workspace_factory()
    suffix = uuid.uuid4().hex[:10]
    email = f"no_ws_member_{suffix}@example.com"
    username = f"no_ws_member_{suffix}"
    reg = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "TestMember403!",
            "full_name": "No Workspace Member",
        },
    )
    assert reg.status_code == 201, reg.text
    user_b_id = int(reg.json()["id"])

    admin_h = _admin_headers(client)
    pre = client.get(f"/api/workspaces/{ws_id}/members", headers=admin_h)
    assert pre.status_code == 200, pre.text
    members = pre.json().get("members") or []
    member_user_ids = {
        int(m["user_id"]) for m in members if m.get("user_id") is not None
    }
    assert user_b_id not in member_user_ids, (
        "Précondition : user_b ne doit pas avoir de membership sur ce workspace "
        f"(members={member_user_ids!r})"
    )

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "TestMember403!"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get(f"/api/workspaces/{ws_id}/members", headers=headers)
    assert r.status_code == 403, r.text
    body = r.json()
    assert "detail" in body
    assert body["detail"]  # réponse d’erreur non vide, sans coupler au libellé exact


def test_mql_stream_persists_mql_query_log(
    client: TestClient,
    db_conn,
) -> None:
    """MQL réel (templates + SQL) ; nettoyage de la ligne de journal en fin de test."""
    marker = f"INTEGRATION_MQL_LOG_{uuid.uuid4().hex}"
    # Requête déterministe → template T1 (défaut) ou autre clé canonique de MQL_TEMPLATES
    query_text = f"{marker} prix médian papier Bamako"

    try:
        headers = _admin_headers(client)
        r = client.post(
            "/api/mql/stream",
            headers=headers,
            json={"query": query_text, "workspace_id": None},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("template_used") in MQL_TEMPLATES, body

        with db_conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, query_text, intent_classified, template_used
                  FROM mql_query_log
                 WHERE query_text = %s
                 ORDER BY created_at DESC
                 LIMIT 1
                """,
                (query_text,),
            )
            row = cur.fetchone()
        assert row is not None, "mql_query_log doit contenir la requête du test"
        assert row["intent_classified"] == "mql_internal"
        assert row["template_used"] == body["template_used"]
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM mql_query_log WHERE query_text = %s", (query_text,)
            )

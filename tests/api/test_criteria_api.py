"""
tests/api/test_criteria_api.py
Tests API — M-CRITERIA-TYPING — DMS V3.3.2

Couverture :
  - POST   /cases/{case_id}/criteria
  - GET    /cases/{case_id}/criteria
  - GET    /cases/{case_id}/criteria/validate/weights
  - GET    /cases/{case_id}/criteria/{criterion_id}
  - DELETE /cases/{case_id}/criteria/{criterion_id}

Règles :
  - db_conn  : fixture root conftest (autocommit=True, dict_row)
  - test_client : fixture tests/api/conftest.py (TestClient)
  - Pas d'import couche_b, pas de psycopg2
  - org_id obligatoire en query param sur GET / DELETE
  - org_id dans le body sur POST
  - Isolation multi-tenant (R7)
  - Gouvernance : DELETE interdit si dossier hors 'draft'
"""

from __future__ import annotations

import uuid

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────


def _create_test_case(db_conn, status: str = "draft") -> str:
    """Crée un dossier de test et retourne son case_id."""
    case_id = f"api-test-{uuid.uuid4().hex[:8]}"
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO cases (id, case_type, title, created_at, status)
            VALUES (%s, 'API_CRITERIA_TEST', %s, NOW()::TEXT, %s)
            """,
            (case_id, f"AO Test Critères {case_id}", status),
        )
    return case_id


def _cleanup(db_conn, case_id: str) -> None:
    """
    Nettoyage robuste :
    1. Repasse en draft (désactive trigger poids DEFERRED)
    2. Supprime criteria
    3. Supprime le case (peut échouer sur memory_entries — ignoré)
    """
    try:
        with db_conn.cursor() as cur:
            cur.execute("UPDATE cases SET status='draft' WHERE id = %s", (case_id,))
    except Exception:  # noqa: BLE001
        pass
    try:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM criteria WHERE case_id = %s", (case_id,))
    except Exception:  # noqa: BLE001
        pass
    try:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM cases WHERE id = %s", (case_id,))
    except Exception:  # noqa: BLE001
        pass


def _post_criterion(
    test_client,
    case_id: str,
    org_id: str = "org-api-test",
    label: str = "Prix rendu site",
    category: str = "commercial",
    weight_pct: float = 60.0,
    scoring_method: str = "formula",
    **kwargs,
) -> dict:
    """Helper POST — retourne la réponse JSON."""
    body = {
        "org_id": org_id,
        "label": label,
        "category": category,
        "weight_pct": weight_pct,
        "scoring_method": scoring_method,
        **kwargs,
    }
    resp = test_client.post(f"/cases/{case_id}/criteria", json=body)
    return resp


# ─────────────────────────────────────────────────────────────
# POST — Créer un critère
# ─────────────────────────────────────────────────────────────


class TestPostCriterion:
    def test_creation_nominale_201(self, test_client, db_conn):
        """POST nominal → 201 + champs conformes."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = _post_criterion(test_client, case_id)
            assert resp.status_code == 201, resp.text
            data = resp.json()
            assert data["case_id"] == case_id
            assert data["org_id"] == "org-api-test"
            assert data["label"] == "Prix rendu site"
            assert data["category"] == "commercial"
            assert abs(data["weight_pct"] - 60.0) < 0.001
            assert data["scoring_method"] == "formula"
            assert data["currency"] == "XOF"
            assert data["is_essential"] is False
            assert "id" in data
            assert "created_at" in data
        finally:
            _cleanup(db_conn, case_id)

    def test_currency_defaut_xof(self, test_client, db_conn):
        """POST sans currency explicite → XOF (Règle R4)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = _post_criterion(test_client, case_id)
            assert resp.status_code == 201
            assert resp.json()["currency"] == "XOF"
        finally:
            _cleanup(db_conn, case_id)

    def test_case_id_introuvable_404(self, test_client):
        """POST case_id inexistant → 404."""
        fake_case = f"inexistant-{uuid.uuid4().hex[:8]}"
        resp = _post_criterion(test_client, fake_case)
        assert resp.status_code == 404
        assert "case_id" in resp.json()["detail"].lower()

    def test_categorie_invalide_422(self, test_client, db_conn):
        """POST category invalide → 422 (Pydantic field_validator)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = _post_criterion(test_client, case_id, category="invalide_xyz")
            assert resp.status_code == 422
        finally:
            _cleanup(db_conn, case_id)

    def test_scoring_method_invalide_422(self, test_client, db_conn):
        """POST scoring_method invalide → 422 (Pydantic field_validator)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = _post_criterion(test_client, case_id, scoring_method="robot_scorer")
            assert resp.status_code == 422
        finally:
            _cleanup(db_conn, case_id)

    def test_poids_negatif_422(self, test_client, db_conn):
        """POST weight_pct < 0 → 422 (Pydantic ge=0)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = _post_criterion(test_client, case_id, weight_pct=-5.0)
            assert resp.status_code == 422
        finally:
            _cleanup(db_conn, case_id)

    def test_poids_superieur_100_422(self, test_client, db_conn):
        """POST weight_pct > 100 → 422 (Pydantic le=100)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = _post_criterion(test_client, case_id, weight_pct=150.0)
            assert resp.status_code == 422
        finally:
            _cleanup(db_conn, case_id)

    def test_label_vide_422(self, test_client, db_conn):
        """POST label vide → 422 (Pydantic min_length=1)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = _post_criterion(test_client, case_id, label="")
            assert resp.status_code == 422
        finally:
            _cleanup(db_conn, case_id)

    def test_canonical_item_id_optionnel(self, test_client, db_conn):
        """POST avec canonical_item_id → OK (R6 : optionnel avant M-NORMALISATION-ITEMS)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = _post_criterion(
                test_client, case_id, canonical_item_id="gasoil-sahel"
            )
            assert resp.status_code == 201
            assert resp.json()["canonical_item_id"] == "gasoil-sahel"
        finally:
            _cleanup(db_conn, case_id)

    def test_is_essential_accepte(self, test_client, db_conn):
        """POST critère essentiel → is_essential=True retourné."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = _post_criterion(
                test_client,
                case_id,
                category="essential",
                is_essential=True,
                weight_pct=0.0,
            )
            assert resp.status_code == 201
            assert resp.json()["is_essential"] is True
        finally:
            _cleanup(db_conn, case_id)


# ─────────────────────────────────────────────────────────────
# GET — Lister les critères d'un dossier
# ─────────────────────────────────────────────────────────────


class TestGetCriteriaList:
    def test_liste_vide(self, test_client, db_conn):
        """GET dossier sans critères → liste vide []."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = test_client.get(
                f"/cases/{case_id}/criteria", params={"org_id": "org-api-test"}
            )
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            _cleanup(db_conn, case_id)

    def test_liste_retourne_critere_cree(self, test_client, db_conn):
        """GET après POST → le critère est présent dans la liste."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            _post_criterion(test_client, case_id)
            resp = test_client.get(
                f"/cases/{case_id}/criteria", params={"org_id": "org-api-test"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["label"] == "Prix rendu site"
        finally:
            _cleanup(db_conn, case_id)

    def test_liste_plusieurs_criteres(self, test_client, db_conn):
        """GET avec plusieurs critères → tous retournés, triés par created_at."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            _post_criterion(test_client, case_id, label="Critère A")
            _post_criterion(test_client, case_id, label="Critère B", weight_pct=40.0)
            resp = test_client.get(
                f"/cases/{case_id}/criteria", params={"org_id": "org-api-test"}
            )
            assert resp.status_code == 200
            assert len(resp.json()) == 2
        finally:
            _cleanup(db_conn, case_id)

    def test_liste_org_id_obligatoire(self, test_client, db_conn):
        """GET sans org_id → 422 (Query obligatoire)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = test_client.get(f"/cases/{case_id}/criteria")
            assert resp.status_code == 422
        finally:
            _cleanup(db_conn, case_id)


# ─────────────────────────────────────────────────────────────
# GET /validate/weights — Somme des poids (R1)
# ─────────────────────────────────────────────────────────────


class TestValidateWeights:
    def test_somme_valide_100_pct(self, test_client, db_conn):
        """validate/weights — somme = 100% → is_valid=True (R1)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            _post_criterion(
                test_client, case_id, label="Critère unique", weight_pct=100.0
            )
            resp = test_client.get(
                f"/cases/{case_id}/criteria/validate/weights",
                params={"org_id": "org-api-test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_valid"] is True
            assert data["status"] == "ok"
            assert data["message"] is None
            assert abs(data["total"] - 100.0) < 0.01
        finally:
            _cleanup(db_conn, case_id)

    def test_somme_invalide_retourne_message(self, test_client, db_conn):
        """validate/weights — somme != 100% → is_valid=False + message (R1)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            _post_criterion(test_client, case_id, weight_pct=60.0)
            resp = test_client.get(
                f"/cases/{case_id}/criteria/validate/weights",
                params={"org_id": "org-api-test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_valid"] is False
            assert data["status"] == "invalid"
            assert data["message"] is not None
            assert abs(data["total"] - 60.0) < 0.01
        finally:
            _cleanup(db_conn, case_id)

    def test_essentiels_exclus_de_la_somme(self, test_client, db_conn):
        """validate/weights — critères essentiels exclus du total (R1)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            # Critère non-essentiel : 100%
            _post_criterion(test_client, case_id, weight_pct=100.0)
            # Critère essentiel : hors somme
            _post_criterion(
                test_client,
                case_id,
                label="Essentiel",
                category="essential",
                weight_pct=0.0,
                is_essential=True,
            )
            resp = test_client.get(
                f"/cases/{case_id}/criteria/validate/weights",
                params={"org_id": "org-api-test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_valid"] is True
            assert abs(data["total"] - 100.0) < 0.01
        finally:
            _cleanup(db_conn, case_id)

    def test_validate_weights_org_id_obligatoire(self, test_client, db_conn):
        """validate/weights sans org_id → 422."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = test_client.get(f"/cases/{case_id}/criteria/validate/weights")
            assert resp.status_code == 422
        finally:
            _cleanup(db_conn, case_id)

    def test_validate_weights_dossier_vide(self, test_client, db_conn):
        """validate/weights dossier sans critères → total=0, is_valid=False."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = test_client.get(
                f"/cases/{case_id}/criteria/validate/weights",
                params={"org_id": "org-api-test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_valid"] is False
            assert data["total"] == 0.0
        finally:
            _cleanup(db_conn, case_id)


# ─────────────────────────────────────────────────────────────
# GET /{criterion_id} — Récupérer un critère
# ─────────────────────────────────────────────────────────────


class TestGetCriterionById:
    def test_get_criterion_ok(self, test_client, db_conn):
        """GET /{criterion_id} → 200 + champs corrects."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            created = _post_criterion(test_client, case_id).json()
            criterion_id = created["id"]
            resp = test_client.get(
                f"/cases/{case_id}/criteria/{criterion_id}",
                params={"org_id": "org-api-test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == criterion_id
            assert data["label"] == "Prix rendu site"
        finally:
            _cleanup(db_conn, case_id)

    def test_get_criterion_introuvable_404(self, test_client, db_conn):
        """GET critère inexistant → 404."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            fake_id = str(uuid.uuid4())
            resp = test_client.get(
                f"/cases/{case_id}/criteria/{fake_id}",
                params={"org_id": "org-api-test"},
            )
            assert resp.status_code == 404
        finally:
            _cleanup(db_conn, case_id)

    def test_get_criterion_org_id_obligatoire(self, test_client, db_conn):
        """GET /{criterion_id} sans org_id → 422."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = test_client.get(f"/cases/{case_id}/criteria/{uuid.uuid4()}")
            assert resp.status_code == 422
        finally:
            _cleanup(db_conn, case_id)


# ─────────────────────────────────────────────────────────────
# DELETE /{criterion_id}
# ─────────────────────────────────────────────────────────────


class TestDeleteCriterion:
    def test_delete_criterion_204(self, test_client, db_conn):
        """DELETE critère en draft → 204 No Content."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            created = _post_criterion(test_client, case_id).json()
            criterion_id = created["id"]
            resp = test_client.delete(
                f"/cases/{case_id}/criteria/{criterion_id}",
                params={"org_id": "org-api-test"},
            )
            assert resp.status_code == 204
            # Vérification : le critère n'existe plus
            resp2 = test_client.get(
                f"/cases/{case_id}/criteria/{criterion_id}",
                params={"org_id": "org-api-test"},
            )
            assert resp2.status_code == 404
        finally:
            _cleanup(db_conn, case_id)

    def test_delete_criterion_introuvable_404(self, test_client, db_conn):
        """DELETE critère inexistant → 404."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            fake_id = str(uuid.uuid4())
            resp = test_client.delete(
                f"/cases/{case_id}/criteria/{fake_id}",
                params={"org_id": "org-api-test"},
            )
            assert resp.status_code == 404
        finally:
            _cleanup(db_conn, case_id)

    def test_delete_gouvernance_hors_draft_404(self, test_client, db_conn):
        """DELETE critère d'un dossier hors 'draft' → 404 (gouvernance)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            # Créer critère avec poids 100% pour satisfaire le trigger DEFERRED
            created = _post_criterion(test_client, case_id, weight_pct=100.0).json()
            criterion_id = created["id"]
            # Passer en evaluation (trigger poids actif au commit)
            with db_conn.cursor() as cur:
                cur.execute(
                    "UPDATE cases SET status='evaluation' WHERE id = %s", (case_id,)
                )
            # Tenter suppression → interdit par règle gouvernance
            resp = test_client.delete(
                f"/cases/{case_id}/criteria/{criterion_id}",
                params={"org_id": "org-api-test"},
            )
            assert resp.status_code == 404
        finally:
            _cleanup(db_conn, case_id)

    def test_delete_org_id_obligatoire(self, test_client, db_conn):
        """DELETE sans org_id → 422."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            resp = test_client.delete(f"/cases/{case_id}/criteria/{uuid.uuid4()}")
            assert resp.status_code == 422
        finally:
            _cleanup(db_conn, case_id)


# ─────────────────────────────────────────────────────────────
# ISOLATION MULTI-TENANT (R7)
# ─────────────────────────────────────────────────────────────


class TestMultiTenantIsolation:
    def test_org_a_ne_voit_pas_criteres_org_b(self, test_client, db_conn):
        """GET org_a ne retourne pas les critères de org_b (R7)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            # org_b crée un critère
            _post_criterion(test_client, case_id, org_id="org-b")
            # org_a liste → liste vide
            resp = test_client.get(
                f"/cases/{case_id}/criteria", params={"org_id": "org-a"}
            )
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            _cleanup(db_conn, case_id)

    def test_org_a_ne_peut_supprimer_critere_org_b(self, test_client, db_conn):
        """DELETE org_a sur critère org_b → 404 (R7)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            # org_b crée
            created = _post_criterion(test_client, case_id, org_id="org-b").json()
            criterion_id = created["id"]
            # org_a tente de supprimer
            resp = test_client.delete(
                f"/cases/{case_id}/criteria/{criterion_id}",
                params={"org_id": "org-a"},
            )
            assert resp.status_code == 404
        finally:
            _cleanup(db_conn, case_id)

    def test_get_criterion_org_incorrect_404(self, test_client, db_conn):
        """GET /{criterion_id} avec mauvais org_id → 404 (R7)."""
        case_id = _create_test_case(db_conn, "draft")
        try:
            created = _post_criterion(test_client, case_id, org_id="org-owner").json()
            criterion_id = created["id"]
            # Tenter d'accéder avec un org_id différent
            resp = test_client.get(
                f"/cases/{case_id}/criteria/{criterion_id}",
                params={"org_id": "org-intrus"},
            )
            assert resp.status_code == 404
        finally:
            _cleanup(db_conn, case_id)

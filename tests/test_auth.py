"""Tests authentification JWT (M4A) — migré M2 vers moteur V4.1.0."""

import uuid

from fastapi.testclient import TestClient
from jose import jwt

from main import app

client = TestClient(app)


def test_login_success():
    """Login admin → token JWT."""
    response = client.post(
        "/auth/token", data={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_initial_setup_forbidden_when_superuser_exists():
    """POST /auth/setup — désactivé dès qu'un superuser existe (seed migration)."""
    response = client.post("/auth/setup")
    assert response.status_code == 403
    assert "setup" in response.json()["detail"].lower()


def test_login_wrong_password():
    """Mauvais mot de passe → 401."""
    response = client.post(
        "/auth/token", data={"username": "admin", "password": "WrongPassword"}
    )
    assert response.status_code == 401


def test_login_nonexistent_user():
    """Utilisateur inexistant → 401."""
    response = client.post(
        "/auth/token", data={"username": "nonexistent", "password": "password"}
    )
    assert response.status_code == 401


def test_register_user():
    """Enregistrement nouvel utilisateur."""
    unique_username = f"testuser_{uuid.uuid4().hex[:8]}"
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "email": unique_email,
            "username": unique_username,
            "password": "testpass",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == unique_username
    assert data["email"] == unique_email
    assert data["role_name"] == "procurement_officer"


def test_register_duplicate_username():
    """Enregistrement avec username existant → 409."""
    response = client.post(
        "/auth/register",
        json={
            "email": "another@example.com",
            "username": "admin",  # Already exists
            "password": "testpass",
        },
    )
    assert response.status_code == 409


def test_get_me_without_auth():
    """Endpoint /me sans token → 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_get_me_with_auth():
    """Endpoint /me avec token valide → 200."""
    # Login
    login_response = client.post(
        "/auth/token", data={"username": "admin", "password": "admin123"}
    )
    token = login_response.json()["access_token"]

    # Accès protégé
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role_name"] == "admin"


def test_invalid_token():
    """Token invalide → 401."""
    response = client.get(
        "/auth/me", headers={"Authorization": "Bearer invalid_token_here"}
    )
    assert response.status_code == 401


def test_protected_endpoint_no_auth():
    """Endpoint protégé sans token → 401."""
    response = client.post(
        "/api/cases", json={"case_type": "DAO", "title": "Test Case", "lot": None}
    )
    # Maintenant l'endpoint exige CurrentUser, donc 401
    assert response.status_code == 401


def test_protected_endpoint_with_token():
    """Endpoint protégé avec token valide → 200."""
    # Login
    login_response = client.post(
        "/auth/token", data={"username": "admin", "password": "admin123"}
    )
    token = login_response.json()["access_token"]

    # Création d'un case
    response = client.post(
        "/api/cases",
        json={"case_type": "DAO", "title": "Test Case with Auth", "lot": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["title"] == "Test Case with Auth"
    assert "owner_id" in data


def test_token_expiration():
    """Test que le token V4.1.0 contient les claims obligatoires."""
    login_response = client.post(
        "/auth/token", data={"username": "admin", "password": "admin123"}
    )
    token = login_response.json()["access_token"]

    # Inspecter le payload sans vérifier la signature
    payload = jwt.get_unverified_claims(token)
    assert "sub" in payload  # user_id
    assert "exp" in payload  # expiration
    assert "jti" in payload  # révocation
    assert "role" in payload  # RBAC
    assert payload.get("type") == "access"


def test_procurement_officer_token_carries_buyer_role():
    """procurement_officer legacy → role='buyer' dans token V4.1.0 (ADR-M2-001 mapping).

    Décision CTO : ROLE_MAPPING["procurement_officer"] = "buyer".
    Ce test ne peut pas être supprimé sans décision explicite.
    roles table : id=2 → procurement_officer → mapped → buyer.
    """
    unique_username = f"po_{uuid.uuid4().hex[:8]}"
    unique_email = f"po_{uuid.uuid4().hex[:8]}@example.com"

    reg = client.post(
        "/auth/register",
        json={
            "email": unique_email,
            "username": unique_username,
            "password": "testpass123",
        },
    )
    assert reg.status_code == 201
    assert reg.json()["role_name"] == "procurement_officer"

    login_response = client.post(
        "/auth/token", data={"username": unique_username, "password": "testpass123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    payload = jwt.get_unverified_claims(token)
    assert payload["role"] == "buyer", f"Attendu 'buyer', obtenu '{payload['role']}'"
    assert payload["role"] != "viewer"

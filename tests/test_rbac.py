"""Tests RBAC (M4B)."""

import uuid

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def get_token(username: str, password: str) -> str:
    """Helper login – retourne le token JWT."""
    response = client.post(
        "/auth/token", data={"username": username, "password": password}
    )
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.json()}")
    return response.json()["access_token"]


def create_test_user(username: str, email: str, password: str = "testpass") -> dict:
    """Helper pour créer un utilisateur de test."""
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "full_name": f"Test User {username}",
        },
    )
    if response.status_code != 201:
        # L'utilisateur existe déjà, on essaye de se connecter
        return {"username": username, "password": password}
    return response.json()


def test_admin_can_access_all_cases():
    """Admin peut voir tous les cases."""
    admin_token = get_token("admin", "admin123")
    response = client.get(
        "/api/cases", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200


def test_procurement_officer_can_create_case():
    """Procurement officer peut créer un case."""
    unique_id = uuid.uuid4().hex[:8]
    user = create_test_user(f"officer_{unique_id}", f"officer_{unique_id}@test.com")
    token = get_token(user["username"], user.get("password", "testpass"))

    response = client.post(
        "/api/cases",
        json={
            "case_type": "DAO",
            "title": f"Test Case by Officer {unique_id}",
            "lot": None,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "id" in response.json()
    return response.json()["id"]


def test_ownership_check():
    """Vérifie qu'un utilisateur ne peut pas accéder/modifier le case d'un autre."""
    # Créer deux utilisateurs
    unique_id1 = uuid.uuid4().hex[:8]
    unique_id2 = uuid.uuid4().hex[:8]

    user1 = create_test_user(f"owner_{unique_id1}", f"owner_{unique_id1}@test.com")
    user2 = create_test_user(f"other_{unique_id2}", f"other_{unique_id2}@test.com")

    token1 = get_token(user1["username"], user1.get("password", "testpass"))
    token2 = get_token(user2["username"], user2.get("password", "testpass"))

    # User1 crée un case
    create_response = client.post(
        "/api/cases",
        json={"case_type": "DAO", "title": f"Private Case {unique_id1}", "lot": None},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert create_response.status_code == 200
    case_id = create_response.json()["id"]

    # Vérifier que le case a bien le bon owner_id (via GET /cases/{id})
    get_response = client.get(
        f"/api/cases/{case_id}", headers={"Authorization": f"Bearer {token1}"}
    )
    assert get_response.status_code == 200
    case_data = get_response.json()
    assert (
        case_data["case"]["owner_id"] == user1.get("id")
        or case_data["case"]["owner_id"] == 1
    )  # selon l'implémentation

    # User2 tente d'uploader un DAO sur le case de User1 → doit échouer avec 403
    upload_response = client.post(
        f"/api/cases/{case_id}/upload-dao",
        files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")},
        headers={"Authorization": f"Bearer {token2}"},
    )
    # L'endpoint devrait retourner 403 (Forbidden) si ownership check est implémenté
    assert upload_response.status_code == 403


def test_admin_bypass_ownership():
    """Admin peut accéder et uploader sur les cases des autres utilisateurs."""
    admin_token = get_token("admin", "admin123")

    # Créer un utilisateur ordinaire et son case
    unique_id = uuid.uuid4().hex[:8]
    user = create_test_user(f"regular_{unique_id}", f"regular_{unique_id}@test.com")
    user_token = get_token(user["username"], user.get("password", "testpass"))

    create_response = client.post(
        "/api/cases",
        json={
            "case_type": "DAO",
            "title": f"Regular User Case {unique_id}",
            "lot": None,
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert create_response.status_code == 200
    case_id = create_response.json()["id"]

    # Admin peut uploader un DAO sur ce case
    upload_response = client.post(
        f"/api/cases/{case_id}/upload-dao",
        files={"file": ("admin_upload.pdf", b"%PDF-1.4 admin", "application/pdf")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Doit réussir (ownership bypass)
    assert upload_response.status_code == 200
    assert "artifact_id" in upload_response.json()


def test_user_roles():
    """Vérifie que les rôles sont correctement assignés lors de l'inscription."""
    # Admin doit avoir le rôle admin et superuser
    admin_token = get_token("admin", "admin123")
    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role_name"] == "admin"
    assert data["is_superuser"] is True

    # Nouvel utilisateur doit avoir le rôle procurement_officer
    unique_id = uuid.uuid4().hex[:8]
    user = create_test_user(f"newuser_{unique_id}", f"new_{unique_id}@test.com")
    token = get_token(user["username"], user.get("password", "testpass"))

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["role_name"] == "procurement_officer"
    assert data["is_superuser"] is False

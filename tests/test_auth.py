"""Tests authentification JWT (M4A)."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_login_success():
    """Login admin → token JWT."""
    response = client.post("/auth/token", data={
        "username": "admin",
        "password": "Admin123!"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password():
    """Mauvais mot de passe → 401."""
    response = client.post("/auth/token", data={
        "username": "admin",
        "password": "WrongPassword"
    })
    assert response.status_code == 401


def test_register_user():
    """Enregistrement nouvel utilisateur."""
    import uuid
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    
    response = client.post("/auth/register", json={
        "email": email,
        "username": username,
        "password": "SecurePass123!",
        "full_name": "Test User"
    })
    assert response.status_code == 201
    assert response.json()["username"] == username


def test_register_duplicate_username():
    """Enregistrement avec username existant → 409."""
    response = client.post("/auth/register", json={
        "email": "admin2@dms.local",
        "username": "admin",  # Already exists
        "password": "SecurePass123!",
        "full_name": "Admin 2"
    })
    assert response.status_code == 409


def test_get_me_without_token():
    """Accès /auth/me sans token → 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_get_me_with_token():
    """Accès /auth/me avec token valide → 200."""
    # Login
    login_response = client.post("/auth/token", data={
        "username": "admin",
        "password": "Admin123!"
    })
    token = login_response.json()["access_token"]
    
    # Get current user
    response = client.get("/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["role_name"] == "admin"


def test_protected_endpoint_no_auth():
    """Endpoint protégé sans token → 401."""
    response = client.post("/api/cases", json={
        "case_type": "DAO",
        "title": "Test Case",
        "lot": None
    })
    assert response.status_code == 401


def test_protected_endpoint_with_token():
    """Endpoint protégé avec token valide → 200."""
    # Login
    login_response = client.post("/auth/token", data={
        "username": "admin",
        "password": "Admin123!"
    })
    token = login_response.json()["access_token"]
    
    # Create case
    response = client.post("/api/cases", 
        json={
            "case_type": "DAO",
            "title": "Test Case with Auth",
            "lot": None
        },
        headers={
            "Authorization": f"Bearer {token}"
        }
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert response.json()["title"] == "Test Case with Auth"


def test_invalid_token():
    """Token invalide → 401."""
    response = client.get("/auth/me", headers={
        "Authorization": "Bearer invalid_token_here"
    })
    assert response.status_code == 401

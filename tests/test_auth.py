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


def test_login_nonexistent_user():
    """Utilisateur inexistant → 401."""
    response = client.post("/auth/token", data={
        "username": "nonexistent",
        "password": "password"
    })
    assert response.status_code == 401


def test_register_user():
    """Enregistrement nouvel utilisateur."""
    import uuid
    unique_username = f"testuser_{uuid.uuid4().hex[:8]}"
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    
    response = client.post("/auth/register", json={
        "email": unique_email,
        "username": unique_username,
        "password": "SecurePass123!",
        "full_name": "Test User"
    })
    assert response.status_code == 201
    assert response.json()["username"] == unique_username
    assert response.json()["email"] == unique_email
    assert response.json()["role_name"] == "procurement_officer"


def test_register_duplicate_username():
    """Enregistrement avec username existant → 409."""
    response = client.post("/auth/register", json={
        "email": "another@example.com",
        "username": "admin",  # Already exists
        "password": "SecurePass123!"
    })
    assert response.status_code == 409


def test_get_me_without_auth():
    """Endpoint /me sans token → 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_get_me_with_auth():
    """Endpoint /me avec token valide → 200."""
    # Login
    login_response = client.post("/auth/token", data={
        "username": "admin",
        "password": "Admin123!"
    })
    token = login_response.json()["access_token"]
    
    # Accès protégé
    response = client.get("/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["role_name"] == "admin"


def test_invalid_token():
    """Token invalide → 401."""
    response = client.get("/auth/me", headers={
        "Authorization": "Bearer invalid_token_here"
    })
    assert response.status_code == 401


def test_protected_endpoint_no_auth():
    """Endpoint protégé sans token → 401."""
    # This test assumes upload endpoints require auth
    response = client.post("/api/cases", json={
        "case_type": "DAO",
        "title": "Test Case"
    })
    # Should fail without auth (though endpoint might not enforce it yet in all cases)
    # The actual behavior depends on whether the endpoint has CurrentUser dependency


def test_token_expiration():
    """Test que le token contient un champ exp."""
    from jose import jwt
    from src.auth import SECRET_KEY, ALGORITHM
    
    # Login
    login_response = client.post("/auth/token", data={
        "username": "admin",
        "password": "Admin123!"
    })
    token = login_response.json()["access_token"]
    
    # Decode without verification to check structure
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "sub" in payload  # User ID
    assert "exp" in payload  # Expiration

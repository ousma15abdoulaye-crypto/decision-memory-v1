"""Authentication & authorization – JWT manual implementation (no ORM).

Constitution V2.1 : Pas de FastAPI-Users (ORM interdit).
Implémentation manuelle avec python-jose + passlib.
"""

import os
from datetime import datetime, timedelta
from functools import wraps
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import text

from src.db import db_execute, db_execute_one, get_connection

# --- Configuration ---
SECRET_KEY = os.getenv("JWT_SECRET", "CHANGE_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 heures

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# --- Password helpers ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie mot de passe avec bcrypt."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash mot de passe avec bcrypt."""
    return pwd_context.hash(password)


# --- User helpers (synchrones, Constitution V2.1) ---
def get_user_by_username(username: str) -> Optional[dict]:
    """Récupère utilisateur par username."""
    with get_connection() as conn:
        return db_execute_one(
            conn,
            """
            SELECT u.*, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = :username
        """,
            {"username": username},
        )


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Récupère utilisateur par ID."""
    with get_connection() as conn:
        return db_execute_one(
            conn,
            """
            SELECT u.*, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = :id
        """,
            {"id": user_id},
        )


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authentifie utilisateur (username + password)."""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    if not user["is_active"]:
        return None

    # Update last_login
    with get_connection() as conn:
        db_execute(
            conn,
            "UPDATE users SET last_login = :ts WHERE id = :id",
            {"ts": datetime.utcnow().isoformat(), "id": user["id"]},
        )

    return user


# --- JWT token helpers ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crée JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Récupère utilisateur actuel depuis JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)  # Convert string back to int
    except (JWTError, ValueError):
        raise credentials_exception

    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Vérifie que utilisateur est actif."""
    if not current_user["is_active"]:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Type alias pour injection dépendances
CurrentUser = Annotated[dict, Depends(get_current_active_user)]
CurrentSuperUser = Annotated[dict, Depends(get_current_active_user)]  # À filtrer par is_superuser


# --- RBAC helpers ---
def get_user_role(user: dict) -> str:
    """Récupère nom du rôle utilisateur."""
    return user.get("role_name", "viewer")


def require_roles(*allowed_roles: str):
    """Décorateur RBAC – vérifie rôles autorisés."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: dict = None, **kwargs):
            # Extraire current_user des kwargs si présent
            if current_user is None:
                # Chercher dans kwargs
                current_user = kwargs.get("current_user") or kwargs.get("user")

            if current_user is None:
                raise HTTPException(403, "Authentication required")

            user_role = get_user_role(current_user)
            if user_role not in allowed_roles and not current_user.get("is_superuser"):
                raise HTTPException(status_code=403, detail=f"Requires one of roles: {', '.join(allowed_roles)}")
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# --- Ownership check ---
def check_case_ownership(case_id: str, user: dict) -> bool:
    """Vérifie que utilisateur est propriétaire du case ou admin."""
    # Admin bypass
    if user.get("is_superuser") or get_user_role(user) == "admin":
        return True

    with get_connection() as conn:
        case = db_execute_one(conn, "SELECT owner_id FROM cases WHERE id = :id", {"id": case_id})
        if not case:
            raise HTTPException(404, "Case not found")

        if case["owner_id"] != user["id"]:
            raise HTTPException(403, "You do not own this case")

    return True


# --- User creation helper ---
def create_user(email: str, username: str, password: str, role_id: int = 2, full_name: str = None) -> dict:
    """Crée nouvel utilisateur."""
    hashed_password = get_password_hash(password)
    timestamp = datetime.utcnow().isoformat()

    with get_connection() as conn:
        # Vérifier unicité email/username
        existing = db_execute_one(
            conn,
            """
            SELECT id FROM users WHERE email = :email OR username = :username
        """,
            {"email": email, "username": username},
        )

        if existing:
            raise HTTPException(409, "Email or username already exists")

        # Insérer utilisateur avec RETURNING pour PostgreSQL
        result = conn.execute(
            text("""
            INSERT INTO users (email, username, hashed_password, full_name, role_id, is_active, is_superuser, created_at)
            VALUES (:email, :username, :password, :name, :role, TRUE, FALSE, :ts)
            RETURNING id
        """),
            {
                "email": email,
                "username": username,
                "password": hashed_password,
                "name": full_name,
                "role": role_id,
                "ts": timestamp,
            },
        )

        user_id = result.fetchone()[0]
        # Fetch the user data within the same transaction to avoid isolation issues
        return db_execute_one(
            conn,
            """
            SELECT u.*, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = :id
        """,
            {"id": user_id},
        )

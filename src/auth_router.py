"""Authentication endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from datetime import timedelta

from src.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    CurrentUser,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from src.ratelimit import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


class Token(BaseModel):
    access_token: str
    token_type: str


class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: str = None


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str = None
    role_name: str
    is_active: bool
    is_superuser: bool


@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint – retourne JWT token."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["id"])},  # Store user ID as string in JWT
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("3/hour")
async def register(request: Request, user_data: UserRegister):
    """Enregistre nouvel utilisateur (role procurement_officer par défaut)."""
    user = create_user(
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        full_name=user_data.full_name,
        role_id=2  # procurement_officer
    )
    return UserResponse(**user)


@router.get("/me", response_model=UserResponse)
@limiter.limit("60/minute")
async def get_me(request: Request, current_user: CurrentUser):
    """Récupère informations utilisateur actuel."""
    return UserResponse(**current_user)

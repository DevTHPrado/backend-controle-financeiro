"""
Auth routes — register and login.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.user import (
    UserCreate,
    UserLogin,
    TokenResponse,
    UserResponse,
    RefreshTokenRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """Register a new user account."""
    try:
        return await auth_service.register_user(db, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: Annotated[AsyncSession, Depends(get_db)]):
    """Authenticate and receive a JWT rotating token pair (access + refresh)."""
    try:
        return await auth_service.authenticate_user(db, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    """Rotate JWT tokens using a valid refresh token."""
    try:
        return await auth_service.refresh_token_pair(db, data.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

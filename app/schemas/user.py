"""Pydantic schemas for User, Auth and Token."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes in seconds


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    preferences: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    preferences: dict | None = None

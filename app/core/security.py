"""
Security utilities: password hashing (Argon2) and JWT token management.
"""

from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings

# Argon2 hasher with secure defaults
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hashed one."""
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a short-lived JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a long-lived JWT refresh token for token rotation."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token. Returns None if invalid or not an access token."""
    return decode_token(token, expected_type="access")


def decode_refresh_token(token: str) -> dict | None:
    """Decode and validate a JWT refresh token. Returns None if invalid or not a refresh token."""
    return decode_token(token, expected_type="refresh")


def decode_token(token: str, expected_type: str | None = None) -> dict | None:
    """Decode and validate a JWT token with optional token type verification."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if expected_type and payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None

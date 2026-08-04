"""
Authentication service — register, login, token generation.
Seeds default categories on user registration.
"""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.models.category import Category
from app.schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse

# Default categories seeded on registration
DEFAULT_CATEGORIES = [
    # Despesas
    {"name": "Alimentação", "type": "DESPESA", "budget_group": "NECESSIDADE"},
    {"name": "Transporte", "type": "DESPESA", "budget_group": "NECESSIDADE"},
    {"name": "Moradia", "type": "DESPESA", "budget_group": "NECESSIDADE"},
    {"name": "Saúde", "type": "DESPESA", "budget_group": "NECESSIDADE"},
    {"name": "Contas (água/luz/internet)", "type": "DESPESA", "budget_group": "NECESSIDADE"},
    {"name": "Educação", "type": "DESPESA", "budget_group": "DESEJO"},
    {"name": "Lazer", "type": "DESPESA", "budget_group": "DESEJO"},
    {"name": "Vestuário", "type": "DESPESA", "budget_group": "DESEJO"},
    {"name": "Poupança/Investimentos", "type": "DESPESA", "budget_group": "POUPANCA"},
    # Receitas
    {"name": "Salário", "type": "RECEITA", "budget_group": None},
    {"name": "Renda Extra", "type": "RECEITA", "budget_group": None},
    {"name": "Investimentos", "type": "RECEITA", "budget_group": None},
]


async def register_user(db: AsyncSession, data: UserCreate) -> UserResponse:
    """Register a new user with hashed password and seed default categories."""
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise ValueError("Email já cadastrado")

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.flush()  # Get user.id before creating categories

    # Seed default categories for the new user
    for cat_data in DEFAULT_CATEGORIES:
        category = Category(user_id=user.id, **cat_data)
        db.add(category)

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


async def authenticate_user(db: AsyncSession, data: UserLogin) -> TokenResponse:
    """Authenticate user by email or username and return JWT token."""
    login_input = data.email.strip()
    result = await db.execute(
        select(User).where(
            (User.email.ilike(login_input)) | (User.name.ilike(login_input))
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise ValueError("Usuário ou senha incorretos")

    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token)

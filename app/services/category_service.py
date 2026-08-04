"""
Category service — CRUD operations scoped to user_id.
"""

import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse


async def get_categories(
    db: AsyncSession, user_id: uuid.UUID, include_inactive: bool = False
) -> list[CategoryResponse]:
    """List all categories for a user."""
    query = select(Category).where(Category.user_id == user_id)
    if not include_inactive:
        query = query.where(Category.is_active == True)
    query = query.order_by(Category.type, Category.name)

    result = await db.execute(query)
    categories = result.scalars().all()
    return [CategoryResponse.model_validate(c) for c in categories]


async def create_category(
    db: AsyncSession, user_id: uuid.UUID, data: CategoryCreate
) -> CategoryResponse:
    """Create a new category for the user."""
    category = Category(user_id=user_id, **data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return CategoryResponse.model_validate(category)


async def update_category(
    db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID, data: CategoryUpdate
) -> CategoryResponse:
    """Update an existing category. Ensures it belongs to the user."""
    result = await db.execute(
        select(Category).where(
            Category.id == category_id, Category.user_id == user_id
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise ValueError("Categoria não encontrada")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    await db.commit()
    await db.refresh(category)
    return CategoryResponse.model_validate(category)


async def delete_category(
    db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID
) -> None:
    """Soft-delete a category (set is_active = False)."""
    result = await db.execute(
        select(Category).where(
            Category.id == category_id, Category.user_id == user_id
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise ValueError("Categoria não encontrada")

    category.is_active = False
    await db.commit()

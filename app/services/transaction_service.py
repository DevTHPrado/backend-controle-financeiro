"""
Transaction service — CRUD with filtering, pagination, and user isolation.
"""

import uuid
import math
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.transaction import Transaction
from app.models.category import Category
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionFilters,
    PaginatedTransactions,
)


async def get_transactions(
    db: AsyncSession, user_id: uuid.UUID, filters: TransactionFilters
) -> PaginatedTransactions:
    """List transactions with filtering and pagination."""
    base_query = select(Transaction).where(Transaction.user_id == user_id)

    # Apply filters
    if filters.start_date:
        base_query = base_query.where(Transaction.transaction_date >= filters.start_date)
    if filters.end_date:
        base_query = base_query.where(Transaction.transaction_date <= filters.end_date)
    if filters.type:
        base_query = base_query.where(Transaction.type == filters.type.value)
    if filters.category_id:
        base_query = base_query.where(Transaction.category_id == filters.category_id)
    if filters.origin:
        base_query = base_query.where(Transaction.origin == filters.origin)

    # Count total
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (filters.page - 1) * filters.per_page
    items_query = (
        base_query
        .options(joinedload(Transaction.category))
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .offset(offset)
        .limit(filters.per_page)
    )
    result = await db.execute(items_query)
    transactions = result.scalars().unique().all()

    items = []
    for t in transactions:
        resp = TransactionResponse.model_validate(t)
        resp.category_name = t.category.name if t.category else None
        items.append(resp)

    return PaginatedTransactions(
        items=items,
        total=total,
        page=filters.page,
        per_page=filters.per_page,
        pages=math.ceil(total / filters.per_page) if filters.per_page else 0,
    )


async def create_transaction(
    db: AsyncSession, user_id: uuid.UUID, data: TransactionCreate
) -> TransactionResponse:
    """Create a new transaction. Validates category ownership."""
    # Verify category belongs to user
    cat_result = await db.execute(
        select(Category).where(
            Category.id == data.category_id, Category.user_id == user_id
        )
    )
    category = cat_result.scalar_one_or_none()
    if not category:
        raise ValueError("Categoria não encontrada ou não pertence ao usuário")

    transaction = Transaction(
        user_id=user_id,
        origin="MANUAL",
        **data.model_dump(),
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    resp = TransactionResponse.model_validate(transaction)
    resp.category_name = category.name
    return resp


async def update_transaction(
    db: AsyncSession, user_id: uuid.UUID, transaction_id: uuid.UUID, data: TransactionUpdate
) -> TransactionResponse:
    """Update an existing transaction."""
    result = await db.execute(
        select(Transaction)
        .options(joinedload(Transaction.category))
        .where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise ValueError("Lançamento não encontrado")

    # If changing category, verify ownership
    update_data = data.model_dump(exclude_unset=True)
    if "category_id" in update_data:
        cat_result = await db.execute(
            select(Category).where(
                Category.id == update_data["category_id"],
                Category.user_id == user_id,
            )
        )
        if not cat_result.scalar_one_or_none():
            raise ValueError("Categoria não encontrada ou não pertence ao usuário")

    for key, value in update_data.items():
        setattr(transaction, key, value)

    await db.commit()
    await db.refresh(transaction)

    # Reload category for name
    cat_result = await db.execute(select(Category).where(Category.id == transaction.category_id))
    cat = cat_result.scalar_one_or_none()

    resp = TransactionResponse.model_validate(transaction)
    resp.category_name = cat.name if cat else None
    return resp


async def delete_transaction(
    db: AsyncSession, user_id: uuid.UUID, transaction_id: uuid.UUID
) -> None:
    """Hard-delete a transaction."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id, Transaction.user_id == user_id
        )
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise ValueError("Lançamento não encontrado")

    await db.delete(transaction)
    await db.commit()

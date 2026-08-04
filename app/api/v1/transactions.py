"""
Transaction routes — CRUD with filtering and pagination.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.category import CategoryType
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionFilters,
    PaginatedTransactions,
)
from app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["Lançamentos"])


@router.get("", response_model=PaginatedTransactions)
async def list_transactions(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    type: CategoryType | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    origin: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List transactions with optional filters and pagination."""
    filters = TransactionFilters(
        start_date=start_date,
        end_date=end_date,
        type=type,
        category_id=category_id,
        origin=origin,
        page=page,
        per_page=per_page,
    )
    return await transaction_service.get_transactions(db, current_user.id, filters)


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new manual transaction."""
    try:
        return await transaction_service.create_transaction(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: uuid.UUID,
    data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing transaction."""
    try:
        return await transaction_service.update_transaction(
            db, current_user.id, transaction_id, data
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a transaction (hard delete)."""
    try:
        await transaction_service.delete_transaction(db, current_user.id, transaction_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

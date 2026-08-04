"""Pydantic schemas for Transaction CRUD and filtering."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.category import CategoryType


class TransactionCreate(BaseModel):
    category_id: uuid.UUID
    type: CategoryType
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    transaction_date: date
    description: str | None = Field(None, max_length=255)


class TransactionUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    type: CategoryType | None = None
    amount: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2)
    transaction_date: date | None = None
    description: str | None = Field(None, max_length=255)


class TransactionResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID | None
    category_name: str | None = None
    type: str
    amount: Decimal
    transaction_date: date
    description: str | None
    origin: str
    import_batch_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionFilters(BaseModel):
    """Query parameters for filtering transactions."""
    start_date: date | None = None
    end_date: date | None = None
    type: CategoryType | None = None
    category_id: uuid.UUID | None = None
    origin: str | None = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class PaginatedTransactions(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    per_page: int
    pages: int

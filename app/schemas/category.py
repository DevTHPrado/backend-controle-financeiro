"""Pydantic schemas for Category CRUD."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CategoryType(str, Enum):
    RECEITA = "RECEITA"
    DESPESA = "DESPESA"


class BudgetGroup(str, Enum):
    NECESSIDADE = "NECESSIDADE"
    DESEJO = "DESEJO"
    POUPANCA = "POUPANCA"


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: CategoryType
    budget_group: BudgetGroup | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    type: CategoryType | None = None
    budget_group: BudgetGroup | None = None
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: CategoryType
    budget_group: BudgetGroup | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

"""
Dashboard routes — aggregated data for charts.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def get_summary(
    month: int | None = Query(None),
    year: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get summary cards: total income, expenses, and balance."""
    return await dashboard_service.get_summary(db, current_user.id, month, year)


@router.get("/monthly")
async def get_monthly_evolution(
    months: int = Query(12, ge=1, le=24),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get monthly income vs expenses evolution."""
    return await dashboard_service.get_monthly_evolution(db, current_user.id, months)


@router.get("/by-category")
async def get_expenses_by_category(
    month: int | None = Query(None),
    year: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get expense distribution by category."""
    return await dashboard_service.get_expenses_by_category(db, current_user.id, month, year)

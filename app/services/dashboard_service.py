"""
Dashboard service — aggregated data for charts and summary cards.
All queries scoped to user_id for multi-tenant isolation.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func, extract, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.category import Category


async def get_summary(
    db: AsyncSession, user_id: uuid.UUID, month: int | None = None, year: int | None = None
) -> dict:
    """Get summary cards: total income, total expenses, balance."""
    today = date.today()
    target_month = month or today.month
    target_year = year or today.year

    query = (
        select(
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .where(
            Transaction.user_id == user_id,
            extract("month", Transaction.transaction_date) == target_month,
            extract("year", Transaction.transaction_date) == target_year,
        )
        .group_by(Transaction.type)
    )

    result = await db.execute(query)
    rows = result.all()

    totals = {"RECEITA": Decimal("0"), "DESPESA": Decimal("0")}
    for row in rows:
        totals[row.type] = row.total

    return {
        "month": target_month,
        "year": target_year,
        "total_receitas": float(totals["RECEITA"]),
        "total_despesas": float(totals["DESPESA"]),
        "saldo": float(totals["RECEITA"] - totals["DESPESA"]),
    }


async def get_monthly_evolution(
    db: AsyncSession, user_id: uuid.UUID, months: int = 12
) -> list[dict]:
    """Get monthly income vs expenses for the last N months."""
    today = date.today()
    start_date = date(today.year, today.month, 1) - timedelta(days=30 * (months - 1))
    start_date = date(start_date.year, start_date.month, 1)

    query = (
        select(
            extract("year", Transaction.transaction_date).label("year"),
            extract("month", Transaction.transaction_date).label("month"),
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
        )
        .group_by(
            extract("year", Transaction.transaction_date),
            extract("month", Transaction.transaction_date),
            Transaction.type,
        )
        .order_by(
            extract("year", Transaction.transaction_date),
            extract("month", Transaction.transaction_date),
        )
    )

    result = await db.execute(query)
    rows = result.all()

    # Group by year-month
    monthly_data: dict[str, dict] = {}
    for row in rows:
        key = f"{int(row.year)}-{int(row.month):02d}"
        if key not in monthly_data:
            monthly_data[key] = {
                "period": key,
                "year": int(row.year),
                "month": int(row.month),
                "receitas": 0.0,
                "despesas": 0.0,
            }
        if row.type == "RECEITA":
            monthly_data[key]["receitas"] = float(row.total)
        else:
            monthly_data[key]["despesas"] = float(row.total)

    # Add saldo to each month
    for data in monthly_data.values():
        data["saldo"] = data["receitas"] - data["despesas"]

    return list(monthly_data.values())


async def get_expenses_by_category(
    db: AsyncSession, user_id: uuid.UUID, month: int | None = None, year: int | None = None
) -> list[dict]:
    """Get expense distribution by category for a specific month."""
    today = date.today()
    target_month = month or today.month
    target_year = year or today.year

    query = (
        select(
            Category.name.label("category"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.type == "DESPESA",
            extract("month", Transaction.transaction_date) == target_month,
            extract("year", Transaction.transaction_date) == target_year,
        )
        .group_by(Category.name)
        .order_by(func.sum(Transaction.amount).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    total_expenses = sum(float(row.total) for row in rows)

    return [
        {
            "category": row.category,
            "total": float(row.total),
            "percentage": round(float(row.total) / total_expenses * 100, 1)
            if total_expenses > 0
            else 0.0,
        }
        for row in rows
    ]

"""
Recommendation engine — objective, mathematical insights.

IMPORTANT: All recommendations are strictly descriptive and comparative.
No prescriptive language ("you should", "I recommend"). Only facts and comparisons.
This avoids legal liability and is technically more reliable.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.transaction import Transaction
from app.models.category import Category
from app.models.user import User


async def generate_recommendations(
    db: AsyncSession, user_id: uuid.UUID, month: int | None = None, year: int | None = None
) -> list[dict]:
    """
    Generate objective financial insights for the user.
    Returns a list of insight dicts: {"type": str, "severity": str, "message": str}
    Severity: "info" | "warning" | "alert"
    """
    today = date.today()
    target_month = month or today.month
    target_year = year or today.year

    insights: list[dict] = []

    # ── 1. Deficit / Surplus ─────────────────────────────────────────
    totals = await _get_monthly_totals(db, user_id, target_month, target_year)
    receitas = totals.get("RECEITA", Decimal("0"))
    despesas = totals.get("DESPESA", Decimal("0"))
    saldo = receitas - despesas

    if saldo < 0:
        insights.append({
            "type": "deficit",
            "severity": "alert",
            "icon": "📉",
            "message": (
                f"Suas despesas superaram suas receitas neste mês. "
                f"Déficit de R$ {abs(saldo):,.2f}."
            ),
        })
    elif saldo > 0:
        insights.append({
            "type": "surplus",
            "severity": "info",
            "icon": "📈",
            "message": (
                f"Você teve um superávit de R$ {saldo:,.2f} neste mês "
                f"(receitas: R$ {receitas:,.2f}, despesas: R$ {despesas:,.2f})."
            ),
        })

    # ── 2. Category above average (3-month comparison) ───────────────
    if receitas > 0:
        category_insights = await _check_categories_vs_average(
            db, user_id, target_month, target_year, receitas
        )
        insights.extend(category_insights)

    # ── 3. Budget rule 50/30/20 ──────────────────────────────────────
    if receitas > 0:
        budget_insights = await _check_budget_rule(
            db, user_id, target_month, target_year, receitas
        )
        insights.extend(budget_insights)

    # ── 4. Month-over-month trend ────────────────────────────────────
    trend_insight = await _check_trend(db, user_id, target_month, target_year)
    if trend_insight:
        insights.append(trend_insight)

    return insights


async def _get_monthly_totals(
    db: AsyncSession, user_id: uuid.UUID, month: int, year: int
) -> dict[str, Decimal]:
    """Get total receitas and despesas for a specific month."""
    query = (
        select(
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .where(
            Transaction.user_id == user_id,
            extract("month", Transaction.transaction_date) == month,
            extract("year", Transaction.transaction_date) == year,
        )
        .group_by(Transaction.type)
    )
    result = await db.execute(query)
    return {row.type: row.total for row in result.all()}


async def _check_categories_vs_average(
    db: AsyncSession,
    user_id: uuid.UUID,
    month: int,
    year: int,
    current_income: Decimal,
) -> list[dict]:
    """Check if any expense category is above its 3-month average relative to income."""
    insights = []

    # Current month expenses by category
    current_query = (
        select(
            Category.name,
            func.sum(Transaction.amount).label("total"),
        )
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.type == "DESPESA",
            extract("month", Transaction.transaction_date) == month,
            extract("year", Transaction.transaction_date) == year,
        )
        .group_by(Category.name)
    )
    current_result = await db.execute(current_query)
    current_cats = {row.name: float(row.total) for row in current_result.all()}

    # Get last 3 months' averages
    target_date = date(year, month, 1)
    for cat_name, cat_total in current_cats.items():
        avg_totals = []
        for i in range(1, 4):
            prev_date = target_date - timedelta(days=30 * i)
            prev_query = (
                select(func.coalesce(func.sum(Transaction.amount), 0))
                .join(Category, Transaction.category_id == Category.id)
                .where(
                    Transaction.user_id == user_id,
                    Transaction.type == "DESPESA",
                    Category.name == cat_name,
                    extract("month", Transaction.transaction_date) == prev_date.month,
                    extract("year", Transaction.transaction_date) == prev_date.year,
                )
            )
            prev_result = await db.execute(prev_query)
            avg_totals.append(float(prev_result.scalar() or 0))

        avg = sum(avg_totals) / 3 if avg_totals else 0
        current_pct = (cat_total / float(current_income)) * 100

        if avg > 0 and cat_total > avg * 1.2:  # 20% above average
            avg_pct = (avg / float(current_income)) * 100
            insights.append({
                "type": "category_above_avg",
                "severity": "warning",
                "icon": "⚠️",
                "message": (
                    f"Gastos com {cat_name} representaram {current_pct:.1f}% da sua renda "
                    f"este mês, acima da média dos últimos 3 meses ({avg_pct:.1f}%)."
                ),
            })

    return insights


async def _check_budget_rule(
    db: AsyncSession,
    user_id: uuid.UUID,
    month: int,
    year: int,
    income: Decimal,
) -> list[dict]:
    """Check spending against the 50/30/20 budget rule."""
    insights = []

    # Get user preferences for custom percentages
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    budget_rule = {"necessidades": 50, "desejos": 30, "poupanca": 20}
    if user and user.preferences and "budget_rule" in user.preferences:
        budget_rule = user.preferences["budget_rule"]

    # Query expenses grouped by budget_group
    query = (
        select(
            Category.budget_group,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.type == "DESPESA",
            Category.budget_group.isnot(None),
            extract("month", Transaction.transaction_date) == month,
            extract("year", Transaction.transaction_date) == year,
        )
        .group_by(Category.budget_group)
    )

    result = await db.execute(query)
    group_totals = {row.budget_group: float(row.total) for row in result.all()}

    income_float = float(income)
    group_labels = {
        "NECESSIDADE": ("Necessidades", budget_rule.get("necessidades", 50)),
        "DESEJO": ("Desejos", budget_rule.get("desejos", 30)),
        "POUPANCA": ("Poupança", budget_rule.get("poupanca", 20)),
    }

    parts = []
    for group_key, (label, ref_pct) in group_labels.items():
        actual = group_totals.get(group_key, 0)
        actual_pct = (actual / income_float * 100) if income_float > 0 else 0
        parts.append(f"{label}: {actual_pct:.1f}% (referência: {ref_pct}%)")

    insights.append({
        "type": "budget_rule",
        "severity": "info",
        "icon": "📊",
        "message": "Regra orçamentária: " + " | ".join(parts),
    })

    return insights


async def _check_trend(
    db: AsyncSession, user_id: uuid.UUID, month: int, year: int
) -> dict | None:
    """Check month-over-month expense trend."""
    # Current month total expenses
    current_total = await _get_total_expenses(db, user_id, month, year)

    # Previous month
    prev_date = date(year, month, 1) - timedelta(days=1)
    prev_total = await _get_total_expenses(db, user_id, prev_date.month, prev_date.year)

    if prev_total > 0 and current_total > 0:
        change_pct = ((current_total - prev_total) / prev_total) * 100

        if abs(change_pct) >= 5:  # Only report if change >= 5%
            direction = "aumentaram" if change_pct > 0 else "diminuíram"
            return {
                "type": "trend",
                "severity": "warning" if change_pct > 15 else "info",
                "icon": "📊" if change_pct <= 0 else "📈",
                "message": (
                    f"Seus gastos totais {direction} {abs(change_pct):.1f}% "
                    f"em relação ao mês anterior "
                    f"(R$ {prev_total:,.2f} → R$ {current_total:,.2f})."
                ),
            }

    return None


async def _get_total_expenses(
    db: AsyncSession, user_id: uuid.UUID, month: int, year: int
) -> float:
    """Get total expenses for a specific month."""
    query = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(
            Transaction.user_id == user_id,
            Transaction.type == "DESPESA",
            extract("month", Transaction.transaction_date) == month,
            extract("year", Transaction.transaction_date) == year,
        )
    )
    result = await db.execute(query)
    return float(result.scalar() or 0)

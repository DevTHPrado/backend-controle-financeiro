"""
Recommendations routes — objective financial insights.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services import recommendation_engine

router = APIRouter(prefix="/recommendations", tags=["Recomendações"])


@router.get("")
async def get_recommendations(
    month: int | None = Query(None),
    year: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get objective financial insights based on transaction data."""
    return await recommendation_engine.generate_recommendations(
        db, current_user.id, month, year
    )

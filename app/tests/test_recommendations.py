"""
Tests for the recommendation engine — verifies objective insight generation.
"""

import pytest
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.recommendation_engine import (
    generate_recommendations,
    _get_monthly_totals,
)


class TestRecommendationLogic:
    """Test recommendation rules with mocked data."""

    @pytest.mark.asyncio
    async def test_deficit_detection(self):
        """Should detect when expenses exceed income."""
        mock_db = AsyncMock()

        # Mock monthly totals: more expenses than income
        with patch(
            "app.services.recommendation_engine._get_monthly_totals",
            return_value={"RECEITA": Decimal("3000"), "DESPESA": Decimal("4000")},
        ), patch(
            "app.services.recommendation_engine._check_categories_vs_average",
            return_value=[],
        ), patch(
            "app.services.recommendation_engine._check_budget_rule",
            return_value=[],
        ), patch(
            "app.services.recommendation_engine._check_trend",
            return_value=None,
        ):
            insights = await generate_recommendations(
                mock_db, uuid.uuid4(), month=1, year=2024
            )

        deficit_insights = [i for i in insights if i["type"] == "deficit"]
        assert len(deficit_insights) == 1
        assert "R$ 1" in deficit_insights[0]["message"]  # R$ 1,000.00
        assert deficit_insights[0]["severity"] == "alert"

    @pytest.mark.asyncio
    async def test_surplus_detection(self):
        """Should detect when income exceeds expenses."""
        mock_db = AsyncMock()

        with patch(
            "app.services.recommendation_engine._get_monthly_totals",
            return_value={"RECEITA": Decimal("5000"), "DESPESA": Decimal("3000")},
        ), patch(
            "app.services.recommendation_engine._check_categories_vs_average",
            return_value=[],
        ), patch(
            "app.services.recommendation_engine._check_budget_rule",
            return_value=[],
        ), patch(
            "app.services.recommendation_engine._check_trend",
            return_value=None,
        ):
            insights = await generate_recommendations(
                mock_db, uuid.uuid4(), month=1, year=2024
            )

        surplus_insights = [i for i in insights if i["type"] == "surplus"]
        assert len(surplus_insights) == 1
        assert "superávit" in surplus_insights[0]["message"]
        assert surplus_insights[0]["severity"] == "info"

    @pytest.mark.asyncio
    async def test_no_prescriptive_language(self):
        """Ensure no prescriptive language is used in any insight."""
        mock_db = AsyncMock()

        FORBIDDEN_PHRASES = [
            "você deveria",
            "recomendo",
            "pare de",
            "invista em",
            "decisão certa",
            "you should",
            "I recommend",
        ]

        with patch(
            "app.services.recommendation_engine._get_monthly_totals",
            return_value={"RECEITA": Decimal("5000"), "DESPESA": Decimal("6000")},
        ), patch(
            "app.services.recommendation_engine._check_categories_vs_average",
            return_value=[
                {
                    "type": "category_above_avg",
                    "severity": "warning",
                    "icon": "⚠️",
                    "message": "Gastos com Lazer representaram 25.0% da sua renda este mês, acima da média dos últimos 3 meses (15.0%).",
                }
            ],
        ), patch(
            "app.services.recommendation_engine._check_budget_rule",
            return_value=[
                {
                    "type": "budget_rule",
                    "severity": "info",
                    "icon": "📊",
                    "message": "Regra orçamentária: Necessidades: 55.0% (referência: 50%) | Desejos: 35.0% (referência: 30%) | Poupança: 10.0% (referência: 20%)",
                }
            ],
        ), patch(
            "app.services.recommendation_engine._check_trend",
            return_value={
                "type": "trend",
                "severity": "warning",
                "icon": "📈",
                "message": "Seus gastos totais aumentaram 20.0% em relação ao mês anterior (R$ 5,000.00 → R$ 6,000.00).",
            },
        ):
            insights = await generate_recommendations(
                mock_db, uuid.uuid4(), month=1, year=2024
            )

        for insight in insights:
            message_lower = insight["message"].lower()
            for phrase in FORBIDDEN_PHRASES:
                assert phrase not in message_lower, (
                    f"Found prescriptive language '{phrase}' in: {insight['message']}"
                )

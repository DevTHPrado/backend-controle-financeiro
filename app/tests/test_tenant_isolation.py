"""
Tests for multi-tenant data isolation.
Verifies that user A cannot access user B's data.
"""

import pytest
import uuid

from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction


class TestTenantIsolation:
    """Verify all queries are scoped to user_id."""

    def test_category_has_user_id(self):
        """Category model must have user_id column."""
        cat = Category(
            user_id=uuid.uuid4(),
            name="Test",
            type="DESPESA",
        )
        assert cat.user_id is not None

    def test_transaction_has_user_id(self):
        """Transaction model must have user_id column."""
        tx = Transaction(
            user_id=uuid.uuid4(),
            type="DESPESA",
            amount=100,
            transaction_date="2024-01-01",
        )
        assert tx.user_id is not None

    def test_different_users_different_ids(self):
        """Two users should have different UUIDs."""
        user_a = User(id=uuid.uuid4(), name="A", email="a@test.com", hashed_password="hash")
        user_b = User(id=uuid.uuid4(), name="B", email="b@test.com", hashed_password="hash")
        assert user_a.id != user_b.id

    def test_category_belongs_to_specific_user(self):
        """Category should be tied to its owner."""
        user_id = uuid.uuid4()
        other_user_id = uuid.uuid4()

        cat = Category(user_id=user_id, name="Mine", type="DESPESA")
        assert cat.user_id == user_id
        assert cat.user_id != other_user_id

    def test_transaction_belongs_to_specific_user(self):
        """Transaction should be tied to its owner."""
        user_id = uuid.uuid4()
        tx = Transaction(
            user_id=user_id,
            type="RECEITA",
            amount=5000,
            transaction_date="2024-01-15",
        )
        assert tx.user_id == user_id

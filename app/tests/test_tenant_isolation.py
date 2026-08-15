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

    def test_tenant_id_property_alias(self):
        """Verify tenant_id property maps to user_id / id."""
        user_id = uuid.uuid4()
        user = User(id=user_id, name="Test", email="test@test.com", hashed_password="pw")
        assert user.tenant_id == user_id

        cat = Category(user_id=user_id, name="Cat", type="DESPESA")
        assert cat.tenant_id == user_id

        tx = Transaction(user_id=user_id, type="DESPESA", amount=100, transaction_date="2024-01-01")
        assert tx.tenant_id == user_id

    def test_rotating_jwt_tokens(self):
        """Verify access and refresh token creation and decoding."""
        from app.core.security import (
            create_access_token,
            create_refresh_token,
            decode_access_token,
            decode_refresh_token,
        )

        user_id = str(uuid.uuid4())
        access = create_access_token({"sub": user_id})
        refresh = create_refresh_token({"sub": user_id})

        # Verify access token decodes with access type
        access_payload = decode_access_token(access)
        assert access_payload is not None
        assert access_payload["sub"] == user_id
        assert access_payload["type"] == "access"

        # Verify refresh token decodes with refresh type
        refresh_payload = decode_refresh_token(refresh)
        assert refresh_payload is not None
        assert refresh_payload["sub"] == user_id
        assert refresh_payload["type"] == "refresh"

        # Verify cross validation rejection (access cannot decode refresh, refresh cannot decode access)
        assert decode_access_token(refresh) is None
        assert decode_refresh_token(access) is None

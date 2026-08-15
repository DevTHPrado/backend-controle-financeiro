"""
User model — multi-tenant anchor.
Every data entity references user_id for tenant isolation.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    preferences: Mapped[dict | None] = mapped_column(
        JSON,
        default=lambda: {
            "budget_rule": {"necessidades": 50, "desejos": 30, "poupanca": 20}
        },
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    categories = relationship("Category", back_populates="user", lazy="selectin")
    transactions = relationship("Transaction", back_populates="user", lazy="selectin")
    import_batches = relationship("ImportBatch", back_populates="user", lazy="selectin")

    @property
    def tenant_id(self) -> uuid.UUID:
        """User is the tenant root."""
        return self.id

    def __repr__(self) -> str:
        return f"<User {self.email}>"

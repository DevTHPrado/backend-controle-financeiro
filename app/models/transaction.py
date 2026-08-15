"""
Transaction model — financial entries (income/expense).
Always scoped to a user_id for multi-tenant isolation.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import String, Date, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # RECEITA | DESPESA
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origin: Mapped[str] = mapped_column(
        String(50), nullable=False, default="MANUAL"
    )  # MANUAL | IMPORT
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_batches.id", ondelete="SET NULL"),
        nullable=True,
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
    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    import_batch = relationship("ImportBatch", back_populates="transactions")

    @property
    def tenant_id(self) -> uuid.UUID:
        """Alias for user_id to enforce multi-tenant domain semantics."""
        return self.user_id

    @tenant_id.setter
    def tenant_id(self, value: uuid.UUID) -> None:
        self.user_id = value

    def __repr__(self) -> str:
        return f"<Transaction {self.type} {self.amount} @ {self.transaction_date}>"

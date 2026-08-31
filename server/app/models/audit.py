from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=False,
        index=True,
    )

    trust_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    bounds_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    budget_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    offer_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)

    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    reasoning_text: Mapped[str] = mapped_column(Text, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    transaction = relationship("Transaction", back_populates="audit_logs")

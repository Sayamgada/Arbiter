from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    transaction_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("buyers.id"),
        nullable=False,
        index=True,
    )

    merchant_id: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )

    proposed_offer: Mapped[dict] = mapped_column(JSON, nullable=False)
    final_offer: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    razorpay_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    buyer = relationship("Buyer", back_populates="transactions")
    product = relationship("Product")
    audit_logs = relationship("AuditLog", back_populates="transaction")

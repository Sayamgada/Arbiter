from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Buyer(Base):
    __tablename__ = "buyers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    buyer_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    identity_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    intent_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    history_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    violation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    behavior_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    trust_scores = relationship("TrustScoreRecord", back_populates="buyer")
    transactions = relationship("Transaction", back_populates="buyer")

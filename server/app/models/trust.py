from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TrustScoreRecord(Base):
    __tablename__ = "trust_score_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("buyers.id"),
        nullable=False,
        index=True,
    )

    session_id: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    score: Mapped[float] = mapped_column(Float, nullable=False)
    sub_scores: Mapped[dict] = mapped_column(JSON, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    buyer = relationship("Buyer", back_populates="trust_scores")

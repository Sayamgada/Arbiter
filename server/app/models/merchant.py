from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MerchantPolicy(Base):
    __tablename__ = "merchant_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    merchant_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    max_discount_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=12.0,
    )

    daily_budget: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=10000.0,
    )

    trust_full_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=80.0,
    )

    trust_restricted_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=40.0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

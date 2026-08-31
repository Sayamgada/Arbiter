from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BudgetLedger(Base):
    __tablename__ = "budget_ledgers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    merchant_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)

    allocated: Mapped[float] = mapped_column(Float, nullable=False)
    used: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    remaining: Mapped[float] = mapped_column(Float, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

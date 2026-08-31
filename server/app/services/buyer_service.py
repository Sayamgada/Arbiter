from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.buyer import Buyer


class BuyerService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_buyer_id(self, buyer_id: str) -> Buyer | None:
        return self.db.scalar(
            select(Buyer).where(Buyer.buyer_id == buyer_id)
        )

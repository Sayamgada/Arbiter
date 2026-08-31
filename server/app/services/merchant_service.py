from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.merchant import MerchantPolicy


class MerchantPolicyService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_merchant_id(
        self,
        merchant_id: str,
    ) -> MerchantPolicy | None:
        return self.db.scalar(
            select(MerchantPolicy).where(
                MerchantPolicy.merchant_id == merchant_id
            )
        )

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product


class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        *,
        product_id: int,
        merchant_id: str,
    ) -> Product | None:
        return self.db.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.merchant_id == merchant_id,
            )
        )

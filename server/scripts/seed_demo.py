from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.buyer import Buyer
from app.models.merchant import MerchantPolicy
from app.models.product import Product


DEMO_MERCHANT_ID = "demo-merchant"
DEMO_BUYER_ID = "demo-buyer"


def seed_demo() -> None:
    db = SessionLocal()

    try:
        # ---------------------------------------------------------
        # Merchant policy
        # ---------------------------------------------------------
        merchant = db.scalar(
            select(MerchantPolicy).where(
                MerchantPolicy.merchant_id == DEMO_MERCHANT_ID
            )
        )

        if merchant is None:
            merchant = MerchantPolicy(
                merchant_id=DEMO_MERCHANT_ID,
                max_discount_pct=12.0,
                daily_budget=10000.0,
                trust_full_threshold=80.0,
                trust_restricted_threshold=40.0,
            )
            db.add(merchant)
        else:
            merchant.max_discount_pct = 12.0
            merchant.daily_budget = 10000.0
            merchant.trust_full_threshold = 80.0
            merchant.trust_restricted_threshold = 40.0

        # ---------------------------------------------------------
        # Buyer
        # ---------------------------------------------------------
        buyer = db.scalar(
            select(Buyer).where(
                Buyer.buyer_id == DEMO_BUYER_ID
            )
        )

        if buyer is None:
            buyer = Buyer(
                buyer_id=DEMO_BUYER_ID,
                identity_confidence=95.0,
                intent_confidence=90.0,
                history_score=90.0,
                violation_count=0,
                behavior_score=95.0,
                is_active=True,
            )
            db.add(buyer)
        else:
            buyer.identity_confidence = 95.0
            buyer.intent_confidence = 90.0
            buyer.history_score = 90.0
            buyer.violation_count = 0
            buyer.behavior_score = 95.0
            buyer.is_active = True

        # ---------------------------------------------------------
        # Product
        # ---------------------------------------------------------
        product = db.scalar(
            select(Product).where(
                Product.merchant_id == DEMO_MERCHANT_ID,
                Product.name == "Premium Headphones",
            )
        )

        if product is None:
            product = Product(
                merchant_id=DEMO_MERCHANT_ID,
                name="Premium Headphones",
                description=(
                    "Wireless premium headphones for the "
                    "Arbiter commerce demonstration."
                ),
                price=10000.0,
                cost=7000.0,
                inventory=25,
            )
            db.add(product)
        else:
            product.description = (
                "Wireless premium headphones for the "
                "Arbiter commerce demonstration."
            )
            product.price = 10000.0
            product.cost = 7000.0
            product.inventory = 25

        db.commit()

        print("Arbiter demo data seeded successfully.")
        print()
        print(f"Merchant: {DEMO_MERCHANT_ID}")
        print(f"Buyer:    {DEMO_BUYER_ID}")
        print(
            f"Product:  {product.name} "
            f"(id={product.id})"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
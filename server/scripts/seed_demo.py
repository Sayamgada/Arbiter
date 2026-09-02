from app.core.database import SessionLocal
from app.models.buyer import Buyer
from app.models.merchant import MerchantPolicy
from app.models.product import Product


DEMO_MERCHANT_ID = "demo-merchant"
DEMO_BUYER_ID = "demo-buyer"


def seed_demo() -> None:
    db = SessionLocal()

    try:
        buyer = (
            db.query(Buyer)
            .filter(Buyer.buyer_id == DEMO_BUYER_ID)
            .first()
        )

        if buyer is None:
            buyer = Buyer(
                buyer_id=DEMO_BUYER_ID,
                identity_confidence=100.0,
                intent_confidence=100.0,
                history_score=100.0,
                violation_count=0,
                behavior_score=100.0,
                is_active=True,
            )
            db.add(buyer)
        else:
            buyer.identity_confidence = 100.0
            buyer.intent_confidence = 100.0
            buyer.history_score = 100.0
            buyer.violation_count = 0
            buyer.behavior_score = 100.0
            buyer.is_active = True

        merchant = (
            db.query(MerchantPolicy)
            .filter(
                MerchantPolicy.merchant_id
                == DEMO_MERCHANT_ID
            )
            .first()
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

        product = (
            db.query(Product)
            .filter(
                Product.merchant_id
                == DEMO_MERCHANT_ID
            )
            .order_by(Product.id.asc())
            .first()
        )

        if product is None:
            product = Product(
                merchant_id=DEMO_MERCHANT_ID,
                name="Arbiter Demo Product",
                description=(
                    "Demo product used for trust-aware "
                    "agentic commerce negotiation."
                ),
                price=10000.0,
                cost=7000.0,
                inventory=25,
            )
            db.add(product)
        else:
            product.name = "Arbiter Demo Product"
            product.description = (
                "Demo product used for trust-aware "
                "agentic commerce negotiation."
            )
            product.price = 10000.0
            product.cost = 7000.0
            product.inventory = 25

        db.commit()

        print("Demo data seeded successfully.")
        print(f"Buyer:    {DEMO_BUYER_ID}")
        print(f"Merchant: {DEMO_MERCHANT_ID}")
        print(f"Product:  {product.name}")
        print(f"Price:    ₹{product.price:.2f}")
        print(f"Cost:     ₹{product.cost:.2f}")
        print(f"Inventory:{product.inventory}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
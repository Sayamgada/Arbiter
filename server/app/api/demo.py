from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.buyer import Buyer
from app.models.merchant import MerchantPolicy
from app.models.product import Product


router = APIRouter(
    prefix="/api/v1/demo",
    tags=["demo"],
)

DEMO_MERCHANT_ID = "demo-merchant"
DEMO_BUYER_ID = "demo-buyer"


@router.get("/context")
def get_demo_context(
    db: Session = Depends(get_db),
):
    buyer = (
        db.query(Buyer)
        .filter(Buyer.buyer_id == DEMO_BUYER_ID)
        .first()
    )

    merchant = (
        db.query(MerchantPolicy)
        .filter(
            MerchantPolicy.merchant_id
            == DEMO_MERCHANT_ID
        )
        .first()
    )

    product = (
        db.query(Product)
        .filter(
            Product.merchant_id
            == DEMO_MERCHANT_ID
        )
        .order_by(Product.id.asc())
        .first()
    )

    if buyer is None:
        raise HTTPException(
            status_code=404,
            detail="Demo buyer not found",
        )

    if merchant is None:
        raise HTTPException(
            status_code=404,
            detail="Demo merchant policy not found",
        )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Demo product not found",
        )

    return {
        "merchant": {
            "merchant_id": merchant.merchant_id,
            "max_discount_pct": merchant.max_discount_pct,
            "daily_budget": merchant.daily_budget,
            "trust_full_threshold": (
                merchant.trust_full_threshold
            ),
            "trust_restricted_threshold": (
                merchant.trust_restricted_threshold
            ),
        },
        "buyer": {
            "buyer_id": buyer.buyer_id,
            "identity_confidence": (
                buyer.identity_confidence
            ),
            "intent_confidence": buyer.intent_confidence,
            "history_score": buyer.history_score,
            "violation_count": buyer.violation_count,
            "behavior_score": buyer.behavior_score,
            "is_active": buyer.is_active,
        },
        "product": {
            "id": product.id,
            "merchant_id": product.merchant_id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "cost": product.cost,
            "inventory": product.inventory,
        },
    }
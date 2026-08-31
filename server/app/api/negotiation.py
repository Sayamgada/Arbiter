from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.api import NegotiationRequest, NegotiationResponse
from app.services.buyer_service import BuyerService
from app.services.decision_controller import NegotiationDecisionController
from app.services.product_service import ProductService
from app.services.transaction_service import TransactionService


router = APIRouter()


@router.post(
    "/api/v1/negotiation/decide",
    response_model=NegotiationResponse,
    tags=["negotiation"],
)
def decide(
    request: NegotiationRequest,
    db: Session = Depends(get_db),
):
    buyer = BuyerService(db).get_by_buyer_id(request.buyer_id)

    if buyer is None:
        raise HTTPException(
            status_code=404,
            detail="Buyer not found",
        )

    if not buyer.is_active:
        raise HTTPException(
            status_code=403,
            detail="Buyer is inactive",
        )

    product = ProductService(db).get_by_id(
        product_id=request.product_id,
        merchant_id=request.merchant_id,
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found for merchant",
        )

    controller = NegotiationDecisionController(get_redis())

    result = controller.decide(
        merchant_id=request.merchant_id,
        period=request.period,
        buyer_signals=request.buyer_signals,
        product_price=request.product_price,
        product_cost=request.product_cost,
        requested_discount_pct=request.requested_discount_pct,
        max_discount_pct=request.max_discount_pct,
        allocated_budget=request.allocated_budget,
    )

    transaction = TransactionService(db).record_decision(
        buyer_id=buyer.id,
        merchant_id=request.merchant_id,
        product_id=product.id,
        proposed_offer={
            "requested_discount_pct": request.requested_discount_pct,
            "product_price": request.product_price,
            "product_cost": request.product_cost,
        },
        result=result,
    )

    return NegotiationResponse(
        transaction_id=transaction.transaction_id,
        decision=result.decision.value,
        authority=result.authority.value,
        trust_score=result.trust_score,
        discount_pct=result.discount_pct,
        discount_value=result.discount_value,
        final_price=result.final_price,
        budget_remaining=result.budget_remaining,
        reason=result.reason,
    )

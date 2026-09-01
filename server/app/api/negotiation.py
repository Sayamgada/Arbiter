from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.api import NegotiationRequest, NegotiationResponse
from app.services.buyer_service import BuyerService
from app.services.decision_controller import NegotiationDecisionController
from app.services.merchant_service import MerchantPolicyService
from app.services.product_service import ProductService
from app.services.transaction_service import TransactionService
from app.agents.buyer_agent import BuyerAgent
from app.agents.session import NegotiationSession
from app.agents.seller_agent import SellerGrowthAgent
from app.core.redis import get_redis
from app.schemas.api import (
    NegotiationRequest,
    NegotiationResponse,
    NegotiationSessionRequest,
    NegotiationSessionResponse,
)
from app.services.decision_controller import NegotiationDecisionController
from app.services.payment_service import PaymentService

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

    merchant_policy = MerchantPolicyService(db).get_by_merchant_id(
        request.merchant_id
    )

    if merchant_policy is None:
        raise HTTPException(
            status_code=404,
            detail="Merchant policy not found",
        )

    controller = NegotiationDecisionController(get_redis())

    result = controller.decide(
        merchant_id=request.merchant_id,
        period=request.period,
        buyer_signals=request.buyer_signals,
        product_price=product.price,
        product_cost=product.cost,
        requested_discount_pct=request.requested_discount_pct,
        max_discount_pct=merchant_policy.max_discount_pct,
        allocated_budget=merchant_policy.daily_budget,
    )
    transaction = TransactionService(db).create_from_decision(
        buyer_id=buyer.id,
        merchant_id=request.merchant_id,
        product_id=product.id,
        proposed_offer={
            "requested_discount_pct": request.requested_discount_pct,
            "product_price": product.price,
            "product_cost": product.cost,
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

@router.post(
    "/api/v1/negotiation/session",
    response_model=NegotiationSessionResponse,
    tags=["negotiation"],
)
def start_session(
    request: NegotiationSessionRequest,
    db: Session = Depends(get_db),
):
    buyer = BuyerService(db).get_by_buyer_id(
        request.buyer_id
    )

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

    merchant_policy = (
        MerchantPolicyService(db).get_by_merchant_id(
            request.merchant_id
        )
    )

    if merchant_policy is None:
        raise HTTPException(
            status_code=404,
            detail="Merchant policy not found",
        )

    controller = NegotiationDecisionController(
        get_redis()
    )

    session_id = (
        f"session_{request.buyer_id}_"
        f"{request.merchant_id}_"
        f"{request.product_id}"
    )

    buyer_agent = BuyerAgent(
        buyer_id=request.buyer_id,
        merchant_id=request.merchant_id,
        product_id=str(request.product_id),
        session_id=session_id,
        target_discount_pct=request.requested_discount_pct,
    )

    seller_agent = SellerGrowthAgent(
        controller=controller,
        merchant_id=request.merchant_id,
        period=request.period,
        buyer_signals=request.buyer_signals,
        max_discount_pct=merchant_policy.max_discount_pct,
        allocated_budget=merchant_policy.daily_budget,
    )

    session = NegotiationSession(
        buyer=buyer_agent,
        seller=seller_agent,
        product_price=product.price,
        product_cost=product.cost,
        max_rounds=request.max_rounds,
    )

    result = session.start()

    return NegotiationSessionResponse(
        session_id=result.session_id,
        status=result.status,
        rounds=result.rounds,
        final_price=result.final_price,
        final_discount_pct=result.final_discount_pct,
        message=result.message,
        messages=result.messages,
    )
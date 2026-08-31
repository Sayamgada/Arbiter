from fastapi import APIRouter

from app.core.redis import get_redis
from app.schemas.api import NegotiationRequest, NegotiationResponse
from app.services.decision_controller import NegotiationDecisionController


router = APIRouter()


@router.post(
    "/api/v1/negotiation/decide",
    response_model=NegotiationResponse,
    tags=["negotiation"],
)
def decide(request: NegotiationRequest):
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

    return NegotiationResponse(
        decision=result.decision.value,
        authority=result.authority.value,
        trust_score=result.trust_score,
        discount_pct=result.discount_pct,
        discount_value=result.discount_value,
        final_price=result.final_price,
        budget_remaining=result.budget_remaining,
        reason=result.reason,
    )

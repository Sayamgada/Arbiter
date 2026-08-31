from pydantic import BaseModel, Field

from app.schemas.negotiation import BuyerSignals


class NegotiationRequest(BaseModel):
    merchant_id: str
    period: str

    buyer_id: str
    product_id: int

    buyer_signals: BuyerSignals

    requested_discount_pct: float = Field(
        ge=0,
        le=100,
    )


class NegotiationResponse(BaseModel):
    transaction_id: str
    decision: str
    authority: str
    trust_score: float
    discount_pct: float
    discount_value: float
    final_price: float
    budget_remaining: float
    reason: str

from pydantic import BaseModel, Field

from app.schemas.negotiation import BuyerSignals


class NegotiationRequest(BaseModel):
    merchant_id: str
    period: str

    buyer_signals: BuyerSignals

    product_price: float = Field(gt=0)
    product_cost: float = Field(ge=0)

    requested_discount_pct: float = Field(ge=0)
    max_discount_pct: float = Field(ge=0)

    allocated_budget: float = Field(ge=0)


class NegotiationResponse(BaseModel):
    decision: str
    authority: str
    trust_score: float
    discount_pct: float
    discount_value: float
    final_price: float
    budget_remaining: float
    reason: str

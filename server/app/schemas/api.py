from pydantic import BaseModel, Field

from app.agents.protocol import AgentResponse, NegotiationMessage
from app.schemas.negotiation import BuyerSignals, NegotiationStatus
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


class NegotiationSessionRequest(BaseModel):
    merchant_id: str
    period: str
    buyer_id: str
    product_id: int
    buyer_signals: BuyerSignals
    requested_discount_pct: float
    max_rounds: int = Field(default=5, ge=1, le=10)

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

class NegotiationSessionResponse(BaseModel):
    session_id: str
    status: NegotiationStatus
    rounds: int
    final_price: float | None
    final_discount_pct: float | None
    message: str
    messages: list[NegotiationMessage | AgentResponse] = Field(
    default_factory=list
    )

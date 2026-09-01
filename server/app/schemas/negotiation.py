
from enum import Enum

from pydantic import BaseModel, Field

from app.agents.protocol import AgentResponse, NegotiationMessage


class AuthorityTier(str, Enum):
    FULL = "full"
    RESTRICTED = "restricted"
    BLOCK = "block"


class DecisionType(str, Enum):
    APPROVE = "approve"
    COUNTER = "counter"
    RESTRICT = "restrict"
    BLOCK = "block"


class NegotiationStatus(str, Enum):
    ACTIVE = "active"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    EXPIRED = "expired"


class BuyerSignals(BaseModel):
    identity_confidence: float = Field(ge=0, le=100)
    intent_confidence: float = Field(ge=0, le=100)
    history_score: float = Field(ge=0, le=100)
    violation_count: int = Field(ge=0)
    behavior_score: float = Field(ge=0, le=100)


class TrustScoreResult(BaseModel):
    score: float = Field(ge=0, le=100)
    authority: AuthorityTier
    sub_scores: dict[str, float]


class OfferRequest(BaseModel):
    product_price: float = Field(gt=0)
    product_cost: float = Field(ge=0)
    inventory: int = Field(ge=0)

    buyer_requested_discount_pct: float = Field(
        ge=0,
        le=100,
        default=0,
    )


class DecisionResult(BaseModel):
    decision: DecisionType
    offer_discount_pct: float = Field(ge=0, le=100)
    offer_price: float = Field(ge=0)
    require_confirmation: bool = False
    reason: str


class NegotiationSessionResult(BaseModel):
    session_id: str
    status: NegotiationStatus
    rounds: int = Field(ge=0)
    final_price: float | None = None
    final_discount_pct: float | None = None
    message: str
    messages: list[
        NegotiationMessage | AgentResponse
    ] = Field(default_factory=list)


class TransactionStatus(str, Enum):
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_CREATED = "payment_created"
    PAYMENT_AUTHORIZED = "payment_authorized"
    COMPLETED = "completed"
    PAYMENT_FAILED = "payment_failed"
    CANCELLED = "cancelled"


class NegotiationSessionRequest(BaseModel):
    merchant_id: str
    period: str
    buyer_id: str
    product_id: int
    buyer_signals: BuyerSignals
    requested_discount_pct: float = Field(
        ge=0,
        le=100,
    )
    max_rounds: int = Field(
        ge=1,
        le=10,
        default=5,
    )
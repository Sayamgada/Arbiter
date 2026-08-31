from enum import Enum

from pydantic import BaseModel, Field


class AuthorityTier(str, Enum):
    FULL = "full"
    RESTRICTED = "restricted"
    BLOCK = "block"


class DecisionType(str, Enum):
    APPROVE = "approve"
    COUNTER = "counter"
    RESTRICT = "restrict"
    BLOCK = "block"


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

from enum import Enum

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    PURCHASE_REQUEST = "purchase_request"
    OFFER = "offer"
    COUNTER_OFFER = "counter_offer"
    ACCEPT = "accept"
    REJECT = "reject"
    FINAL = "final"


class NegotiationMessage(BaseModel):
    session_id: str
    buyer_id: str
    merchant_id: str
    product_id: str

    message_type: MessageType

    round_number: int = Field(ge=1)

    proposed_price: float = Field(gt=0)
    requested_discount_pct: float = Field(
        ge=0,
        le=100,
        default=0,
    )

    message: str = ""


class AgentResponse(BaseModel):
    session_id: str
    round_number: int
    message_type: MessageType
    price: float = Field(gt=0)
    discount_pct: float = Field(
        ge=0,
        le=100,
    )
    discount_value: float = Field(
        ge=0,
        default=0,
    )
    message: str
    requires_confirmation: bool = False
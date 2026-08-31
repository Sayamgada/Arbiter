from app.agents.protocol import (
    AgentResponse,
    MessageType,
    NegotiationMessage,
)


class BuyerAgent:
    """
    Simulated buyer-side agent.

    Supports deterministic personas for the hackathon demo:
    - cooperative
    - price_sensitive
    - aggressive
    """

    def __init__(
        self,
        *,
        buyer_id: str,
        merchant_id: str,
        product_id: str,
        session_id: str,
        target_discount_pct: float,
        persona: str = "cooperative",
    ):
        if target_discount_pct < 0 or target_discount_pct > 100:
            raise ValueError(
                "Target discount must be between 0 and 100"
            )

        self.buyer_id = buyer_id
        self.merchant_id = merchant_id
        self.product_id = product_id
        self.session_id = session_id
        self.target_discount_pct = target_discount_pct
        self.persona = persona

    def create_purchase_request(
        self,
        *,
        product_price: float,
    ) -> NegotiationMessage:
        if product_price <= 0:
            raise ValueError(
                "Product price must be positive"
            )

        requested_price = (
            product_price
            * (1 - self.target_discount_pct / 100)
        )

        return NegotiationMessage(
            session_id=self.session_id,
            buyer_id=self.buyer_id,
            merchant_id=self.merchant_id,
            product_id=self.product_id,
            message_type=MessageType.PURCHASE_REQUEST,
            round_number=1,
            proposed_price=round(requested_price, 2),
            requested_discount_pct=self.target_discount_pct,
            message=self._request_message(),
        )

    def respond_to_offer(
        self,
        *,
        price: float,
        discount_pct: float,
        round_number: int,
    ) -> AgentResponse:
        if price <= 0:
            raise ValueError(
                "Offer price must be positive"
            )

        if discount_pct >= self.target_discount_pct:
            return AgentResponse(
                session_id=self.session_id,
                round_number=round_number,
                message_type=MessageType.ACCEPT,
                price=price,
                discount_pct=discount_pct,
                message=(
                    "That works for me. "
                    "I accept the offer."
                ),
            )

        return AgentResponse(
            session_id=self.session_id,
            round_number=round_number,
            message_type=MessageType.COUNTER_OFFER,
            price=price,
            discount_pct=discount_pct,
            message=(
                f"I was hoping for a discount closer to "
                f"{self.target_discount_pct:.1f}%."
            ),
        )

    def _request_message(self) -> str:
        if self.persona == "aggressive":
            return (
                f"I need a {self.target_discount_pct:.1f}% "
                "discount to proceed."
            )

        if self.persona == "price_sensitive":
            return (
                f"Could you offer around "
                f"{self.target_discount_pct:.1f}% off?"
            )

        return (
            f"I'd like to purchase this with a "
            f"{self.target_discount_pct:.1f}% discount."
        )
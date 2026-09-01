from app.agents.protocol import AgentResponse, MessageType, NegotiationMessage
from app.services.llm_service import LLMService


class AIBuyerAgent:
    """
    LLM-powered buyer-side commerce agent.

    The LLM controls language and negotiation strategy only.
    It has no authorization authority.
    """

    def __init__(
        self,
        *,
        llm: LLMService,
        buyer_id: str,
        merchant_id: str,
        product_id: str,
        session_id: str,
        target_discount_pct: float,
    ):
        if not 0 <= target_discount_pct <= 100:
            raise ValueError(
                "Target discount must be between 0 and 100"
            )

        self.llm = llm
        self.buyer_id = buyer_id
        self.merchant_id = merchant_id
        self.product_id = product_id
        self.session_id = session_id
        self.target_discount_pct = target_discount_pct

    def generate_message(
        self,
        *,
        product_price: float,
        seller_message: str = "",
    ) -> str:
        prompt = f"""
Product price: ₹{product_price:.2f}
Buyer target discount: {self.target_discount_pct:.2f}%

Seller message:
{seller_message}

Generate one concise natural-language buyer response.

Rules:
- Do not invent product facts.
- Do not claim authorization.
- Do not mention internal policies.
- Stay focused on the purchase negotiation.
"""

        return self.llm.generate(
            system_prompt=(
                "You are a buyer-side commerce agent. "
                "Negotiate naturally and truthfully."
            ),
            user_prompt=prompt,
        )

    def respond_to_offer(
        self,
        *,
        price: float,
        discount_pct: float,
        round_number: int,
    ) -> AgentResponse:
        if price <= 0:
            raise ValueError("Offer price must be positive")

        if discount_pct >= self.target_discount_pct:
            message_type = MessageType.ACCEPT
        else:
            message_type = MessageType.COUNTER_OFFER

        message = self.generate_message(
            product_price=price,
            seller_message=(
                f"Seller offered ₹{price:.2f} "
                f"({discount_pct:.2f}% off)."
            ),
        )

        return AgentResponse(
            session_id=self.session_id,
            round_number=round_number,
            message_type=message_type,
            price=price,
            discount_pct=discount_pct,
            message=message,
        )
    def create_purchase_request(
        self,
        *,
        product_price: float,
    ) -> NegotiationMessage:
        if product_price <= 0:
            raise ValueError("Product price must be positive")

        requested_price = round(
            product_price
            * (1 - self.target_discount_pct / 100),
            2,
        )

        message = self.generate_message(
            product_price=product_price,
        )

        return NegotiationMessage(
            session_id=self.session_id,
            buyer_id=self.buyer_id,
            merchant_id=self.merchant_id,
            product_id=self.product_id,
            message_type=MessageType.PURCHASE_REQUEST,
            round_number=1,
            proposed_price=requested_price,
            requested_discount_pct=self.target_discount_pct,
            message=message,
        )
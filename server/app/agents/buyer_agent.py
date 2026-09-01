from app.agents.protocol import (
    AgentResponse,
    MessageType,
    NegotiationMessage,
)
from app.services.llm_service import LLMService


class BuyerAgent:
    """
    Simulated buyer-side agent.

    The LLM is responsible only for natural-language generation.
    Structured negotiation values remain deterministic.

    Supported personas:
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
        llm_service: LLMService | None = None,
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
        self.llm = llm_service

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
            message=self._request_message(
                product_price=product_price,
                requested_price=requested_price,
            ),
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
            message = self._accept_message(
                price=price,
                discount_pct=discount_pct,
            )

            return AgentResponse(
                session_id=self.session_id,
                round_number=round_number,
                message_type=MessageType.ACCEPT,
                price=price,
                discount_pct=discount_pct,
                message=message,
            )

        message = self._counter_message(
            price=price,
            discount_pct=discount_pct,
        )

        return AgentResponse(
            session_id=self.session_id,
            round_number=round_number,
            message_type=MessageType.COUNTER_OFFER,
            price=price,
            discount_pct=discount_pct,
            message=message,
        )

    def _request_message(
        self,
        *,
        product_price: float,
        requested_price: float,
    ) -> str:
        if self.llm is None:
            return self._request_message_fallback()

        return self.llm.generate(
            system_prompt=(
                "You are a buyer-side commerce agent. "
                "Generate concise, natural negotiation language. "
                "Do not invent prices or discounts. "
                "Use only the supplied values."
            ),
            user_prompt=(
                f"Persona: {self.persona}\n"
                f"Product price: ₹{product_price:.2f}\n"
                f"Target discount: "
                f"{self.target_discount_pct:.1f}%\n"
                f"Target price: ₹{requested_price:.2f}\n\n"
                "Write one short purchase request."
            ),
        )

    def _accept_message(
        self,
        *,
        price: float,
        discount_pct: float,
    ) -> str:
        if self.llm is None:
            return (
                "That works for me. "
                "I accept the offer."
            )

        return self.llm.generate(
            system_prompt=(
                "You are a buyer-side commerce agent. "
                "Respond naturally and briefly when accepting "
                "a seller's authorized offer."
            ),
            user_prompt=(
                f"The seller offered ₹{price:.2f} "
                f"({discount_pct:.2f}% off).\n"
                "Write a concise acceptance."
            ),
        )

    def _counter_message(
        self,
        *,
        price: float,
        discount_pct: float,
    ) -> str:
        if self.llm is None:
            return (
                f"I was hoping for a discount closer to "
                f"{self.target_discount_pct:.1f}%."
            )

        return self.llm.generate(
            system_prompt=(
                "You are a buyer-side commerce agent. "
                "Generate a concise counter-negotiation message. "
                "Do not invent or alter the target discount."
            ),
            user_prompt=(
                f"Seller offer: ₹{price:.2f}\n"
                f"Seller discount: {discount_pct:.2f}%\n"
                f"Buyer target discount: "
                f"{self.target_discount_pct:.1f}%\n\n"
                "Write one short counter-offer message."
            ),
        )

    def _request_message_fallback(self) -> str:
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

    def _generate_message(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        fallback: str,
    ) -> str:
        if self.llm is None:
            return fallback

        try:
            response = self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            if response:
                return response

        except Exception:
            pass

        return fallback
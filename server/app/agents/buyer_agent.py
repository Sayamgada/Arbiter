from app.agents.protocol import (
    AgentResponse,
    MessageType,
    NegotiationMessage,
)
from app.services.llm_service import LLMService


class BuyerAgent:
    """
    Simulated buyer-side negotiation agent.

    The buyer knows its own desired outcome but does not know
    merchant-side constraints.

    Private information:
    - target discount
    - minimum acceptable discount
    - persona

    The buyer never receives:
    - merchant ceiling
    - merchant cost
    - merchant budget
    - trust thresholds

    Numerical negotiation decisions remain deterministic.
    """

    VALID_PERSONAS = {
        "cooperative",
        "price_sensitive",
        "aggressive",
    }

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
        if not 0 <= target_discount_pct <= 100:
            raise ValueError(
                "Target discount must be between 0 and 100"
            )

        if persona not in self.VALID_PERSONAS:
            raise ValueError(
                "Unsupported buyer persona"
            )

        self.buyer_id = buyer_id
        self.merchant_id = merchant_id
        self.product_id = product_id
        self.session_id = session_id

        # Buyer's ideal opening request.
        self.target_discount_pct = (
            target_discount_pct
        )

        self.persona = persona
        self.llm = llm_service

        self.product_price: float | None = None

        # Private reservation point.
        self.minimum_acceptable_discount_pct = (
            self._calculate_minimum_acceptable_discount()
        )

        self.current_discount_pct = (
            target_discount_pct
        )

    def create_purchase_request(
        self,
        *,
        product_price: float,
    ) -> NegotiationMessage:

        if product_price <= 0:
            raise ValueError(
                "Product price must be positive"
            )

        self.product_price = product_price
        self.current_discount_pct = (
            self.target_discount_pct
        )

        requested_price = (
            product_price
            * (
                1
                - self.target_discount_pct / 100
            )
        )

        return NegotiationMessage(
            session_id=self.session_id,
            buyer_id=self.buyer_id,
            merchant_id=self.merchant_id,
            product_id=self.product_id,
            message_type=MessageType.PURCHASE_REQUEST,
            round_number=1,
            proposed_price=round(
                requested_price,
                2,
            ),
            requested_discount_pct=(
                self.target_discount_pct
            ),
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

        if not 0 <= discount_pct <= 100:
            raise ValueError(
                "Seller discount must be between 0 and 100"
            )

        if self.product_price is None:
            self.product_price = round(
                price / (1 - discount_pct / 100),
                2,
            )

        # ---------------------------------------------------------
        # ACCEPT
        # ---------------------------------------------------------
        if (
            discount_pct
            >= self.minimum_acceptable_discount_pct
        ):
            self.current_discount_pct = (
                discount_pct
            )

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

        # ---------------------------------------------------------
        # COUNTER
        # ---------------------------------------------------------
        gap = (
            self.target_discount_pct
            - discount_pct
        )

        # Defensive handling.
        if gap <= 0:
            self.current_discount_pct = (
                discount_pct
            )

            return AgentResponse(
                session_id=self.session_id,
                round_number=round_number,
                message_type=MessageType.ACCEPT,
                price=price,
                discount_pct=discount_pct,
                message=self._accept_message(
                    price=price,
                    discount_pct=discount_pct,
                ),
            )

        movement_factor = (
            self._buyer_movement_factor()
        )

        counter_discount = (
            discount_pct
            + gap * movement_factor
        )

        counter_discount = min(
            counter_discount,
            self.target_discount_pct,
        )

        counter_discount = round(
            counter_discount,
            2,
        )

        counter_price = round(
            self.product_price
            * (
                1
                - counter_discount / 100
            ),
            2,
        )

        self.current_discount_pct = (
            counter_discount
        )

        message = self._counter_message(
            price=counter_price,
            discount_pct=counter_discount,
        )

        return AgentResponse(
            session_id=self.session_id,
            round_number=round_number,
            message_type=MessageType.COUNTER_OFFER,
            price=counter_price,
            discount_pct=counter_discount,
            message=message,
        )

    def _calculate_minimum_acceptable_discount(
        self,
    ) -> float:
        """
        Buyer's private reservation point.

        This value is never sent to the seller.
        """

        if self.persona == "aggressive":
            factor = 0.90

        elif self.persona == "price_sensitive":
            factor = 0.80

        else:
            factor = 0.70

        return round(
            self.target_discount_pct * factor,
            2,
        )

    def _buyer_movement_factor(self) -> float:
        """
        Determines how readily the buyer improves its offer.
        """

        if self.persona == "cooperative":
            return 0.50

        if self.persona == "price_sensitive":
            return 0.30

        return 0.20

    def _request_message(
        self,
        *,
        product_price: float,
        requested_price: float,
    ) -> str:

        return self._generate_message(
            system_prompt=(
                "You are a buyer-side commerce agent. "
                "Generate concise, natural negotiation language. "
                "Use only the supplied numerical values. "
                "Do not invent or alter prices or discounts."
            ),
            user_prompt=(
                f"Persona: {self.persona}\n"
                f"Product price: ₹{product_price:.2f}\n"
                f"Requested discount: "
                f"{self.target_discount_pct:.2f}%\n"
                f"Requested price: ₹{requested_price:.2f}\n\n"
                "Write one short purchase request."
            ),
            fallback=self._request_message_fallback(),
            llm=self.llm,
        )

    def _accept_message(
        self,
        *,
        price: float,
        discount_pct: float,
    ) -> str:

        return self._generate_message(
            system_prompt=(
                "You are a buyer-side commerce agent. "
                "Write a concise acceptance of the seller's "
                "offer. Preserve the supplied numerical values."
            ),
            user_prompt=(
                f"Seller offer: ₹{price:.2f}\n"
                f"Discount: {discount_pct:.2f}%\n\n"
                "Write a concise acceptance."
            ),
            fallback=(
                "That works for me. "
                "I accept the offer."
            ),
            llm=self.llm,
        )

    def _counter_message(
        self,
        *,
        price: float,
        discount_pct: float,
    ) -> str:

        return self._generate_message(
            system_prompt=(
                "You are a buyer-side commerce agent. "
                "Generate a concise counter-offer. "
                "Preserve the supplied numerical values exactly. "
                "Do not invent or alter prices or discounts."
            ),
            user_prompt=(
                f"Buyer counter-offer: ₹{price:.2f}\n"
                f"Discount: {discount_pct:.2f}%\n\n"
                "Write one short counter-offer."
            ),
            fallback=(
                f"I can move to {discount_pct:.2f}% off, "
                f"bringing the price to ₹{price:.2f}."
            ),
            llm=self.llm,
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

    @staticmethod
    def _generate_message(
        *,
        system_prompt: str,
        user_prompt: str,
        fallback: str,
        llm: LLMService | None = None,
    ) -> str:

        if llm is None:
            return fallback

        try:
            response = llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            if response:
                return response

        except Exception:
            pass

        return fallback
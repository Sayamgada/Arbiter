from app.agents.protocol import (
    AgentResponse,
    MessageType,
    NegotiationMessage,
)
from app.schemas.negotiation import (
    BuyerSignals,
    DecisionType,
)
from app.services.decision_controller import (
    NDCResult,
    NegotiationDecisionController,
)
from app.services.llm_service import LLMService


class SellerGrowthAgent:
    """
    Merchant-side negotiation agent.

    The Seller Growth Agent does not independently authorize
    discounts.

    Every numerical seller offer passes through the deterministic
    Negotiation Decision Controller.

    The agent remembers its previous concession so that negotiation
    can progress rationally across rounds.

    The LLM only generates language. It cannot change:
    - price
    - discount
    - trust
    - budget
    - merchant ceiling
    - authorization decision
    """

    def __init__(
        self,
        *,
        controller: NegotiationDecisionController,
        merchant_id: str,
        period: str,
        buyer_signals: BuyerSignals,
        max_discount_pct: float,
        allocated_budget: float,
        llm_service: LLMService | None = None,
    ):
        self.controller = controller
        self.merchant_id = merchant_id
        self.period = period
        self.buyer_signals = buyer_signals
        self.max_discount_pct = max_discount_pct
        self.allocated_budget = allocated_budget
        self.llm = llm_service

        # Last deterministic NDC result.
        self.last_decision_result: NDCResult | None = None

        # Seller's previous negotiation position.
        self.last_offer_discount_pct: float | None = None


    def evaluate_offer(
        self,
        request: NegotiationMessage,
        *,
        product_price: float,
        product_cost: float,
        inventory: int | None = None,
    ) -> AgentResponse:

        if request.requested_discount_pct is None:
            raise ValueError(
                "Negotiation request must contain "
                "requested discount"
            )

        result = self.controller.decide(
            merchant_id=self.merchant_id,
            period=self.period,
            buyer_signals=self.buyer_signals,
            product_price=product_price,
            product_cost=product_cost,
            requested_discount_pct=(
                request.requested_discount_pct
            ),
            max_discount_pct=self.max_discount_pct,
            allocated_budget=self.allocated_budget,
            reserve_budget=False,
            round_number=request.round_number,
            previous_discount_pct=(
                self.last_offer_discount_pct
            ),
            inventory=inventory,
        )

        self.last_decision_result = result

        # ---------------------------------------------------------
        # BLOCK
        # ---------------------------------------------------------

        if result.decision == DecisionType.BLOCK:
            return AgentResponse(
                session_id=request.session_id,
                round_number=request.round_number,
                message_type=MessageType.REJECT,
                price=product_price,
                discount_pct=0.0,
                discount_value=0.0,
                message=result.reason,
            )

        # ---------------------------------------------------------
        # REMEMBER SELLER POSITION
        # ---------------------------------------------------------

        self.last_offer_discount_pct = result.discount_pct

        # ---------------------------------------------------------
        # MAP NDC DECISION TO MESSAGE TYPE
        # ---------------------------------------------------------

        if result.decision == DecisionType.APPROVE:
            message_type = MessageType.FINAL

        elif result.decision == DecisionType.RESTRICT:
            message_type = MessageType.OFFER

        else:
            message_type = MessageType.COUNTER_OFFER

        # ---------------------------------------------------------
        # SELLER LANGUAGE
        # ---------------------------------------------------------

        message = self._build_message(
            decision=result.decision,
            discount_pct=result.discount_pct,
            final_price=result.final_price,
            reason=result.reason,
        )

        # ---------------------------------------------------------
        # RESPONSE
        # ---------------------------------------------------------

        return AgentResponse(
            session_id=request.session_id,
            round_number=request.round_number,
            message_type=message_type,
            price=result.final_price,
            discount_pct=result.discount_pct,
            discount_value=result.discount_value,
            requires_confirmation=(
                result.decision == DecisionType.RESTRICT
            ),
            message=message,
        )
        
    def authorize_accepted_offer(
        self,
        *,
        product_price: float,
        product_cost: float,
        discount_pct: float,
    ) -> NDCResult:
        """
        Perform final NDC authorization after the buyer accepts
        the seller's negotiated offer.
        """

        result = self.controller.authorize_accepted_offer(
            merchant_id=self.merchant_id,
            period=self.period,
            buyer_signals=self.buyer_signals,
            product_price=product_price,
            product_cost=product_cost,
            discount_pct=discount_pct,
            max_discount_pct=self.max_discount_pct,
            allocated_budget=self.allocated_budget,
        )

        self.last_decision_result = result

        return result
    def _build_message(
        self,
        *,
        decision: DecisionType,
        discount_pct: float,
        final_price: float,
        reason: str,
    ) -> str:

        fallback = self._fallback_message(
            decision=decision,
            discount_pct=discount_pct,
            final_price=final_price,
            reason=reason,
        )

        if self.llm is None:
            return fallback

        try:
            response = self.llm.generate(
                system_prompt=(
                    "You are the seller-side commerce agent "
                    "for Arbiter. "
                    "Generate concise and professional "
                    "negotiation language. "
                    "The deterministic transaction controller "
                    "has already authorized the numerical offer. "
                    "You MUST preserve the supplied price and "
                    "discount exactly. "
                    "You MUST NOT invent, change, or negotiate "
                    "numerical values."
                ),
                user_prompt=(
                    f"Decision: {decision.value}\n"
                    f"Authorized discount: "
                    f"{discount_pct:.2f}%\n"
                    f"Authorized final price: "
                    f"₹{final_price:.2f}\n"
                    f"Controller reasoning: {reason}\n\n"
                    "Write one short seller response."
                ),
            )

            if response:
                return response

        except Exception:
            pass

        return fallback

    @staticmethod
    def _fallback_message(
        *,
        decision: DecisionType,
        discount_pct: float,
        final_price: float,
        reason: str,
    ) -> str:

        if decision == DecisionType.RESTRICT:
            return (
                f"I can offer {discount_pct:.2f}% off, "
                f"bringing the price to ₹{final_price:.2f}. "
                "Confirmation is required."
            )

        if decision == DecisionType.COUNTER:
            return (
                f"I can offer {discount_pct:.2f}% off, "
                f"bringing the price to ₹{final_price:.2f}."
            )

        return (
            f"I can offer {discount_pct:.2f}% off, "
            f"bringing the price to ₹{final_price:.2f}. "
            "That works for me."
        )
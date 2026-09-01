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
    NegotiationDecisionController,
)
from app.services.llm_service import LLMService


class SellerGrowthAgent:
    """
    Merchant-side negotiation agent.

    The Seller Growth Agent does not have independent
    authorization authority.

    Every proposed offer must pass through the NDC.

    The LLM is used only to generate natural-language
    negotiation responses. It never determines:
    - discount authorization
    - budget usage
    - trust
    - transaction approval
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

    def evaluate_offer(
        self,
        request: NegotiationMessage,
        *,
        product_price: float,
        product_cost: float,
    ) -> AgentResponse:

        # NDC is the sole source of authorization.
        result = self.controller.decide(
            merchant_id=self.merchant_id,
            period=self.period,
            buyer_signals=self.buyer_signals,
            product_price=product_price,
            product_cost=product_cost,
            requested_discount_pct=request.requested_discount_pct,
            max_discount_pct=self.max_discount_pct,
            allocated_budget=self.allocated_budget,
            reserve_budget=False,
        )

        if result.decision == DecisionType.BLOCK:
            return AgentResponse(
                session_id=request.session_id,
                round_number=request.round_number,
                message_type=MessageType.REJECT,
                price=product_price,
                discount_pct=0,
                message=result.reason,
            )

        if result.decision == DecisionType.APPROVE:
            message_type = MessageType.FINAL
        elif result.decision == DecisionType.RESTRICT:
            message_type = MessageType.OFFER
        else:
            message_type = MessageType.COUNTER_OFFER

        message = self._build_message(
            decision=result.decision,
            discount_pct=result.discount_pct,
            final_price=result.final_price,
            reason=result.reason,
        )

        return AgentResponse(
            session_id=request.session_id,
            round_number=request.round_number,
            message_type=message_type,
            price=result.final_price,
            discount_pct=result.discount_pct,
            requires_confirmation=(
                result.decision == DecisionType.RESTRICT
            ),
            message=message,
        )

    def commit_accepted_offer(
        self,
        *,
        discount_value: float,
    ):
        """
        Commit the authorized discount after the buyer
        accepts the offer.
        """
        return self.controller.commit_offer(
            merchant_id=self.merchant_id,
            period=self.period,
            discount_value=discount_value,
        )

    def _build_message(
        self,
        *,
        decision: DecisionType,
        discount_pct: float,
        final_price: float,
        reason: str,
    ) -> str:
        """
        Generate natural-language seller communication.

        All numerical values come from the deterministic NDC result.
        The LLM cannot change them.
        """

        if self.llm is None:
            return self._fallback_message(
                decision=decision,
                discount_pct=discount_pct,
                final_price=final_price,
                reason=reason,
            )

        return self.llm.generate(
            system_prompt=(
                "You are the seller-side commerce agent for Arbiter. "
                "Generate concise, professional negotiation language. "
                "You MUST preserve the supplied price and discount exactly. "
                "You MUST NOT invent, change, or negotiate numerical values. "
                "The authorization decision has already been made by "
                "the deterministic transaction controller."
            ),
            user_prompt=(
                f"Decision: {decision.value}\n"
                f"Authorized discount: {discount_pct:.2f}%\n"
                f"Authorized final price: ₹{final_price:.2f}\n"
                f"Controller reasoning: {reason}\n\n"
                "Write one short seller response to the buyer."
            ),
        )

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
                f"Confirmation is required. {reason}."
            )

        return (
            f"I can offer {discount_pct:.2f}% off, "
            f"bringing the price to ₹{final_price:.2f}. "
            f"{reason}."
        )
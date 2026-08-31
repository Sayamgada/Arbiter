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


class SellerGrowthAgent:
    """
    Merchant-side negotiation agent.

    The Seller Growth Agent does not have independent
    authorization authority.

    Every proposed offer must pass through the NDC.
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
    ):
        self.controller = controller
        self.merchant_id = merchant_id
        self.period = period
        self.buyer_signals = buyer_signals
        self.max_discount_pct = max_discount_pct
        self.allocated_budget = allocated_budget

    def evaluate_offer(
        self,
        request: NegotiationMessage,
        *,
        product_price: float,
        product_cost: float,
    ) -> AgentResponse:

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

        return AgentResponse(
            session_id=request.session_id,
            round_number=request.round_number,
            message_type=message_type,
            price=result.final_price,
            discount_pct=result.discount_pct,
            requires_confirmation=(
                result.decision == DecisionType.RESTRICT
            ),
            message=self._build_message(
                result.discount_pct,
                result.final_price,
                result.reason,
            ),
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

    @staticmethod
    def _build_message(
        discount_pct: float,
        final_price: float,
        reason: str,
    ) -> str:
        return (
            f"I can offer {discount_pct:.2f}% off, "
            f"bringing the price to ₹{final_price:.2f}. "
            f"{reason}."
        )
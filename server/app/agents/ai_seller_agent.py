from app.agents.protocol import AgentResponse, MessageType, NegotiationMessage
from app.schemas.negotiation import BuyerSignals, DecisionType
from app.services.decision_controller import NegotiationDecisionController
from app.services.llm_service import LLMService


class AISellerGrowthAgent:
    """
    LLM-powered merchant negotiation agent.

    Groq generates natural-language negotiation responses.
    The NDC remains the sole authority for discounts and budget.
    """

    def __init__(
        self,
        *,
        llm: LLMService,
        controller: NegotiationDecisionController,
        merchant_id: str,
        period: str,
        buyer_signals: BuyerSignals,
        max_discount_pct: float,
        allocated_budget: float,
    ):
        self.llm = llm
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

        # The LLM does NOT determine authorization.
        # NDC makes the actual decision.
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
        else:
            message_type = MessageType.OFFER

        message = self._generate_message(
            product_price=product_price,
            discount_pct=result.discount_pct,
            final_price=result.final_price,
            reason=result.reason,
            buyer_message=request.message,
        )

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

    def commit_accepted_offer(
        self,
        *,
        discount_value: float,
    ):
        return self.controller.commit_offer(
            merchant_id=self.merchant_id,
            period=self.period,
            discount_value=discount_value,
        )

    def _generate_message(
        self,
        *,
        product_price: float,
        discount_pct: float,
        final_price: float,
        reason: str,
        buyer_message: str,
    ) -> str:

        prompt = f"""
You are the seller-side commerce agent.

Product price: ₹{product_price:.2f}
Authorized discount: {discount_pct:.2f}%
Authorized final price: ₹{final_price:.2f}

Buyer message:
{buyer_message}

Internal decision reason:
{reason}

Generate one concise, natural seller response.

Rules:
- You MUST use exactly the authorized discount and final price.
- Never offer a larger discount.
- Never invent product facts.
- Never mention internal trust scores, budgets, or NDC.
- Never claim payment has been completed.
- Do not modify the authorized price.
"""

        return self.llm.generate(
            system_prompt=(
                "You are a merchant-side commerce agent. "
                "Communicate an already-authorized commercial offer. "
                "You have no authority to change the offer."
            ),
            user_prompt=prompt,
        )
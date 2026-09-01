from app.agents.ai_seller_agent import AISellerGrowthAgent
from app.agents.protocol import MessageType, NegotiationMessage
from app.schemas.negotiation import BuyerSignals, DecisionType
from app.services.decision_controller import NDCResult


class FakeLLM:
    def generate(self, *, system_prompt, user_prompt):
        return "I can offer you the authorized price."


class FakeController:
    def __init__(self, result):
        self.result = result

    def decide(self, **kwargs):
        return self.result

    def commit_offer(self, **kwargs):
        return None


def make_result(
    *,
    decision=DecisionType.APPROVE,
):
    return NDCResult(
        decision=decision,
        authority="full",
        trust_score=90,
        discount_pct=10,
        discount_value=100,
        final_price=900,
        budget_remaining=900,
        reason="Offer is within merchant policy.",
    )


def make_request():
    return NegotiationMessage(
        session_id="session_1",
        buyer_id="buyer_1",
        merchant_id="merchant_1",
        product_id="product_1",
        message_type=MessageType.PURCHASE_REQUEST,
        round_number=1,
        proposed_price=850,
        requested_discount_pct=15,
        message="Can you give me 15% off?",
    )


def test_ai_seller_uses_ndc_authorized_offer():
    agent = AISellerGrowthAgent(
        llm=FakeLLM(),
        controller=FakeController(make_result()),
        merchant_id="merchant_1",
        period="2026-09-01",
        buyer_signals=BuyerSignals(
            identity_confidence=90,
            intent_confidence=90,
            history_score=90,
            violation_count=0,
            behavior_score=90,
        ),
        max_discount_pct=12,
        allocated_budget=1000,
    )

    response = agent.evaluate_offer(
        make_request(),
        product_price=1000,
        product_cost=700,
    )

    assert response.discount_pct == 10
    assert response.price == 900
    assert response.message_type == MessageType.FINAL


def test_ai_seller_blocks_when_ndc_blocks():
    result = make_result(
        decision=DecisionType.BLOCK,
    )

    agent = AISellerGrowthAgent(
        llm=FakeLLM(),
        controller=FakeController(result),
        merchant_id="merchant_1",
        period="2026-09-01",
        buyer_signals=BuyerSignals(
            identity_confidence=10,
            intent_confidence=10,
            history_score=10,
            violation_count=5,
            behavior_score=10,
        ),
        max_discount_pct=12,
        allocated_budget=1000,
    )

    response = agent.evaluate_offer(
        make_request(),
        product_price=1000,
        product_cost=700,
    )

    assert response.message_type == MessageType.REJECT
    assert response.discount_pct == 0
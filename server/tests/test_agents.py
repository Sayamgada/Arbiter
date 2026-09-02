from app.agents.buyer_agent import BuyerAgent
from app.agents.protocol import MessageType
from app.agents.seller_agent import SellerGrowthAgent
from app.core.redis import get_redis
from app.schemas.negotiation import BuyerSignals
from app.services.decision_controller import (
    NegotiationDecisionController,
)
from app.schemas.negotiation import DecisionType


def make_signals(
    identity=100,
    intent=100,
    history=100,
    violations=0,
    behavior=100,
):
    return BuyerSignals(
        identity_confidence=identity,
        intent_confidence=intent,
        history_score=history,
        violation_count=violations,
        behavior_score=behavior,
    )


def make_controller():
    redis = get_redis()
    redis.flushdb()
    return NegotiationDecisionController(redis)


def test_buyer_creates_purchase_request():
    buyer = BuyerAgent(
        buyer_id="buyer-1",
        merchant_id="merchant-1",
        product_id="product-1",
        session_id="session-1",
        target_discount_pct=10,
    )

    request = buyer.create_purchase_request(
        product_price=10000,
    )

    assert request.message_type == MessageType.PURCHASE_REQUEST
    assert request.proposed_price == 9000
    assert request.requested_discount_pct == 10
    assert request.round_number == 1


def test_buyer_accepts_sufficient_offer():
    buyer = BuyerAgent(
        buyer_id="buyer-1",
        merchant_id="merchant-1",
        product_id="product-1",
        session_id="session-1",
        target_discount_pct=10,
    )

    response = buyer.respond_to_offer(
        price=9000,
        discount_pct=10,
        round_number=2,
    )

    assert response.message_type == MessageType.ACCEPT
    assert response.discount_pct == 10
    assert response.price == 9000


def test_buyer_counters_insufficient_offer():
    buyer = BuyerAgent(
        buyer_id="buyer-1",
        merchant_id="merchant-1",
        product_id="product-1",
        session_id="session-1",
        target_discount_pct=10,
    )

    response = buyer.respond_to_offer(
        price=9500,
        discount_pct=5,
        round_number=2,
    )

    assert response.message_type == MessageType.COUNTER_OFFER
    assert response.discount_pct > 5
    assert response.discount_pct <= 10
    assert response.price < 9500


def test_buyer_counter_price_matches_discount():
    buyer = BuyerAgent(
        buyer_id="buyer-1",
        merchant_id="merchant-1",
        product_id="product-1",
        session_id="session-1",
        target_discount_pct=10,
    )

    buyer.create_purchase_request(
        product_price=10000,
    )

    response = buyer.respond_to_offer(
        price=9550,
        discount_pct=4.5,
        round_number=2,
    )

    assert response.message_type == MessageType.COUNTER_OFFER

    expected_price = round(
        10000 * (1 - response.discount_pct / 100),
        2,
    )

    assert response.price == expected_price


def test_seller_opens_with_strategic_counter_offer():
    controller = make_controller()

    seller = SellerGrowthAgent(
        controller=controller,
        merchant_id="merchant-1",
        period="test",
        buyer_signals=make_signals(),
        max_discount_pct=12,
        allocated_budget=5000,
    )

    buyer = BuyerAgent(
        buyer_id="buyer-1",
        merchant_id="merchant-1",
        product_id="product-1",
        session_id="session-1",
        target_discount_pct=10,
    )

    request = buyer.create_purchase_request(
        product_price=10000,
    )

    response = seller.evaluate_offer(
        request,
        product_price=10000,
        product_cost=7000,
    )

    assert response.message_type == MessageType.COUNTER_OFFER

    # Seller should not automatically grant the buyer's request.
    assert 0 < response.discount_pct < 10

    # Merchant ceiling remains a hard boundary.
    assert response.discount_pct <= 12

    # Seller must never price below cost.
    assert response.price >= 7000

    # The seller is only evaluating the offer at this stage.
    assert controller.budget_manager.remaining(
        merchant_id="merchant-1",
        period="test",
    ) == 5000


def test_seller_offer_does_not_consume_budget():
    controller = make_controller()

    seller = SellerGrowthAgent(
        controller=controller,
        merchant_id="merchant-1",
        period="test",
        buyer_signals=make_signals(),
        max_discount_pct=12,
        allocated_budget=5000,
    )

    buyer = BuyerAgent(
        buyer_id="buyer-1",
        merchant_id="merchant-1",
        product_id="product-1",
        session_id="session-1",
        target_discount_pct=10,
    )

    request = buyer.create_purchase_request(
        product_price=10000,
    )

    response = seller.evaluate_offer(
        request,
        product_price=10000,
        product_cost=7000,
    )

    assert response.message_type == MessageType.COUNTER_OFFER
    assert response.discount_pct < 10
    assert response.discount_pct <= 12
    assert response.price >= 7000

    assert controller.budget_manager.remaining(
        merchant_id="merchant-1",
        period="test",
    ) == 5000


def test_seller_commits_budget_after_acceptance():
    controller = make_controller()

    seller = SellerGrowthAgent(
        controller=controller,
        merchant_id="merchant-1",
        period="test",
        buyer_signals=make_signals(),
        max_discount_pct=12,
        allocated_budget=5000,
    )

    buyer = BuyerAgent(
        buyer_id="buyer-1",
        merchant_id="merchant-1",
        product_id="product-1",
        session_id="session-1",
        target_discount_pct=10,
    )

    buyer.create_purchase_request(
        product_price=10000,
    )

    # Seller evaluates the opening request.
    seller_response = seller.evaluate_offer(
        NegotiationMessageForTest.purchase_request(
            buyer_id="buyer-1",
            merchant_id="merchant-1",
            product_id="product-1",
            session_id="session-1",
            price=9000,
            discount_pct=10,
        ),
        product_price=10000,
        product_cost=7000,
    )

    # The seller's opening offer should not reserve budget.
    assert controller.budget_manager.remaining(
        merchant_id="merchant-1",
        period="test",
    ) == 5000

    # A 7% seller offer is within the buyer's cooperative
    # reservation point and should therefore be accepted.
    buyer_response = buyer.respond_to_offer(
        price=9300,
        discount_pct=7,
        round_number=2,
    )

    assert buyer_response.message_type == MessageType.ACCEPT
    assert buyer_response.discount_pct == 7
    assert buyer_response.price == 9300

    authorization = seller.authorize_accepted_offer(
        product_price=10000,
        product_cost=7000,
        discount_pct=7,
    )

    assert authorization.decision == DecisionType.APPROVE
    assert authorization.discount_pct == 7
    assert authorization.discount_value == 700
    assert authorization.final_price == 9300
    assert authorization.budget_remaining == 4300

    assert controller.budget_manager.remaining(
        merchant_id="merchant-1",
        period="test",
    ) == 4300


class NegotiationMessageForTest:
    """
    Small test-only helper to avoid depending on unrelated
    construction details when testing seller budget commitment.
    """

    @staticmethod
    def purchase_request(
        *,
        buyer_id,
        merchant_id,
        product_id,
        session_id,
        price,
        discount_pct,
    ):
        from app.agents.protocol import NegotiationMessage

        return NegotiationMessage(
            session_id=session_id,
            buyer_id=buyer_id,
            merchant_id=merchant_id,
            product_id=product_id,
            message_type=MessageType.PURCHASE_REQUEST,
            round_number=1,
            proposed_price=price,
            requested_discount_pct=discount_pct,
            message="I'd like to purchase this with a 10% discount.",
        )
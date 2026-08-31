from app.agents.buyer_agent import BuyerAgent
from app.agents.protocol import MessageType
from app.agents.seller_agent import SellerGrowthAgent
from app.core.redis import get_redis
from app.schemas.negotiation import BuyerSignals
from app.services.decision_controller import (
    NegotiationDecisionController,
)


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

    assert response.message_type == MessageType.FINAL
    assert response.discount_pct == 10

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

    request = buyer.create_purchase_request(
        product_price=10000,
    )

    seller_response = seller.evaluate_offer(
        request,
        product_price=10000,
        product_cost=7000,
    )

    buyer_response = buyer.respond_to_offer(
        price=seller_response.price,
        discount_pct=seller_response.discount_pct,
        round_number=2,
    )

    assert buyer_response.message_type == MessageType.ACCEPT

    reservation = seller.commit_accepted_offer(
        discount_value=1000,
    )

    assert reservation.allowed is True
    assert reservation.remaining == 4000
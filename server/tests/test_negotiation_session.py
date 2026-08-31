from app.agents.buyer_agent import BuyerAgent
from app.agents.session import (
    NegotiationSession,
    NegotiationStatus,
)
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


def make_session(
    *,
    target_discount_pct=10,
    max_discount_pct=12,
    signals=None,
    budget=5000,
    max_rounds=5,
):
    redis = get_redis()
    redis.flushdb()

    controller = NegotiationDecisionController(redis)

    buyer = BuyerAgent(
        buyer_id="buyer-1",
        merchant_id="merchant-1",
        product_id="product-1",
        session_id="session-1",
        target_discount_pct=target_discount_pct,
    )

    seller = SellerGrowthAgent(
        controller=controller,
        merchant_id="merchant-1",
        period="test",
        buyer_signals=signals or make_signals(),
        max_discount_pct=max_discount_pct,
        allocated_budget=budget,
    )

    return NegotiationSession(
        buyer=buyer,
        seller=seller,
        product_price=10000,
        product_cost=7000,
        max_rounds=max_rounds,
    )


def test_successful_negotiation():
    session = make_session(
        target_discount_pct=10,
    )

    result = session.start()

    assert result.status == NegotiationStatus.ACCEPTED
    assert result.final_price == 9000
    assert result.final_discount_pct == 10
    assert result.rounds == 1


def test_hard_ceiling_controls_negotiation():
    session = make_session(
        target_discount_pct=20,
        max_discount_pct=12,
    )

    result = session.start()

    assert result.status == NegotiationStatus.EXPIRED
    assert result.final_price is None
    assert result.final_discount_pct is None


def test_low_trust_buyer_is_blocked():
    session = make_session(
        target_discount_pct=10,
        signals=make_signals(
            identity=10,
            intent=10,
            history=10,
            violations=5,
            behavior=10,
        ),
    )

    result = session.start()

    assert result.status == NegotiationStatus.BLOCKED
    assert result.final_price is None


def test_budget_is_committed_only_after_acceptance():
    session = make_session(
        target_discount_pct=10,
        budget=5000,
    )

    result = session.start()

    assert result.status == NegotiationStatus.ACCEPTED

    remaining = session.seller.controller.budget_manager.remaining(
        merchant_id="merchant-1",
        period="test",
    )

    assert remaining == 4000


def test_multiple_rounds_can_expire():
    session = make_session(
        target_discount_pct=20,
        max_discount_pct=12,
        max_rounds=3,
    )

    result = session.start()

    assert result.status == NegotiationStatus.EXPIRED
    assert result.rounds == 3
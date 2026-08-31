from app.core.redis import get_redis
from app.schemas.negotiation import AuthorityTier, BuyerSignals, DecisionType
from app.services.decision_controller import NegotiationDecisionController


def make_controller():
    redis = get_redis()
    redis.flushdb()
    return NegotiationDecisionController(redis)


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


def test_approves_valid_offer():
    controller = make_controller()

    result = controller.decide(
        merchant_id="test",
        period="test",
        buyer_signals=make_signals(),
        product_price=10000,
        product_cost=7000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=5000,
    )

    assert result.decision == DecisionType.APPROVE
    assert result.authority == AuthorityTier.FULL
    assert result.discount_pct == 10
    assert result.discount_value == 1000
    assert result.final_price == 9000
    assert result.budget_remaining == 4000


def test_discount_cannot_exceed_merchant_ceiling():
    controller = make_controller()

    result = controller.decide(
        merchant_id="ceiling",
        period="test",
        buyer_signals=make_signals(),
        product_price=10000,
        product_cost=7000,
        requested_discount_pct=30,
        max_discount_pct=12,
        allocated_budget=5000,
    )

    assert result.decision == DecisionType.APPROVE
    assert result.discount_pct == 12
    assert result.discount_value == 1200
    assert result.final_price == 8800


def test_budget_limits_offer():
    controller = make_controller()

    result = controller.decide(
        merchant_id="budget",
        period="test",
        buyer_signals=make_signals(),
        product_price=10000,
        product_cost=7000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=500,
    )

    assert result.discount_pct == 5
    assert result.discount_value == 500
    assert result.final_price == 9500
    assert result.budget_remaining == 0


def test_blocks_low_trust_buyer():
    controller = make_controller()

    result = controller.decide(
        merchant_id="blocked",
        period="test",
        buyer_signals=make_signals(
            identity=10,
            intent=10,
            history=10,
            violations=5,
            behavior=10,
        ),
        product_price=10000,
        product_cost=7000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=5000,
    )

    assert result.decision == DecisionType.BLOCK
    assert result.authority == AuthorityTier.BLOCK
    assert result.discount_pct == 0
    assert result.discount_value == 0
    assert result.final_price == 10000


def test_rejects_offer_below_cost():
    controller = make_controller()

    result = controller.decide(
        merchant_id="margin",
        period="test",
        buyer_signals=make_signals(),
        product_price=10000,
        product_cost=9500,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=5000,
    )

    assert result.final_price >= 9500


def test_insufficient_budget_does_not_overspend():
    controller = make_controller()

    result = controller.decide(
        merchant_id="empty",
        period="test",
        buyer_signals=make_signals(),
        product_price=10000,
        product_cost=7000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=500,
    )

    assert result.discount_value <= 500
    assert result.budget_remaining >= 0

def test_offer_can_be_evaluated_without_reserving_budget():
    controller = make_controller()

    result = controller.decide(
        merchant_id="multiround",
        period="test",
        buyer_signals=make_signals(),
        product_price=10000,
        product_cost=7000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=5000,
        reserve_budget=False,
    )

    assert result.decision == DecisionType.APPROVE
    assert result.discount_value == 1000
    assert result.budget_remaining == 5000

    assert controller.budget_manager.remaining(
        merchant_id="multiround",
        period="test",
    ) == 5000


def test_authorized_offer_can_be_committed_later():
    controller = make_controller()

    result = controller.decide(
        merchant_id="commit",
        period="test",
        buyer_signals=make_signals(),
        product_price=10000,
        product_cost=7000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=5000,
        reserve_budget=False,
    )

    reservation = controller.commit_offer(
        merchant_id="commit",
        period="test",
        discount_value=result.discount_value,
    )

    assert reservation.allowed is True
    assert reservation.remaining == 4000
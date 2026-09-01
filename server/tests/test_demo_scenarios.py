from app.core.redis import get_redis
from app.schemas.negotiation import BuyerSignals, DecisionType
from app.services.decision_controller import NegotiationDecisionController


def make_controller():
    redis = get_redis()
    redis.flushdb()
    return NegotiationDecisionController(redis)


def signals(
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


def test_demo_high_trust_buyer_gets_discount():
    controller = make_controller()

    result = controller.decide(
        merchant_id="demo_high_trust",
        period="demo",
        buyer_signals=signals(),
        product_price=50000,
        product_cost=35000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=10000,
    )

    assert result.decision == DecisionType.APPROVE
    assert result.discount_pct == 10
    assert result.final_price == 45000
    assert result.budget_remaining == 5000


def test_demo_discount_ceiling_is_enforced():
    controller = make_controller()

    result = controller.decide(
        merchant_id="demo_ceiling",
        period="demo",
        buyer_signals=signals(),
        product_price=50000,
        product_cost=35000,
        requested_discount_pct=30,
        max_discount_pct=12,
        allocated_budget=10000,
    )

    assert result.discount_pct == 12
    assert result.final_price == 44000
    assert result.discount_value == 6000


def test_demo_low_trust_buyer_is_blocked():
    controller = make_controller()

    result = controller.decide(
        merchant_id="demo_block",
        period="demo",
        buyer_signals=signals(
            identity=10,
            intent=10,
            history=10,
            violations=5,
            behavior=10,
        ),
        product_price=50000,
        product_cost=35000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=10000,
    )

    assert result.decision == DecisionType.BLOCK
    assert result.discount_pct == 0
    assert result.final_price == 50000


def test_demo_restricted_buyer_requires_restriction():
    controller = make_controller()

    result = controller.decide(
        merchant_id="demo_restricted",
        period="demo",
        buyer_signals=signals(
            identity=70,
            intent=70,
            history=70,
            behavior=70,
        ),
        product_price=50000,
        product_cost=35000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=10000,
    )

    assert result.decision == DecisionType.RESTRICT
    assert result.discount_pct == 10


def test_demo_budget_caps_discount():
    controller = make_controller()

    result = controller.decide(
        merchant_id="demo_budget",
        period="demo",
        buyer_signals=signals(),
        product_price=50000,
        product_cost=35000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=2000,
    )

    assert result.discount_value == 2000
    assert result.discount_pct == 4
    assert result.final_price == 48000
    assert result.budget_remaining == 0


def test_demo_budget_cannot_be_overspent():
    controller = make_controller()

    first = controller.decide(
        merchant_id="demo_overspend",
        period="demo",
        buyer_signals=signals(),
        product_price=50000,
        product_cost=35000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=2000,
    )

    second = controller.decide(
        merchant_id="demo_overspend",
        period="demo",
        buyer_signals=signals(),
        product_price=50000,
        product_cost=35000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=2000,
    )

    assert first.discount_value == 2000
    assert first.budget_remaining == 0

    assert second.discount_value == 0
    assert second.budget_remaining == 0
    assert second.decision == DecisionType.RESTRICT


def test_demo_margin_protection():
    controller = make_controller()

    result = controller.decide(
        merchant_id="demo_margin",
        period="demo",
        buyer_signals=signals(),
        product_price=50000,
        product_cost=48000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=10000,
    )

    assert result.final_price >= 48000
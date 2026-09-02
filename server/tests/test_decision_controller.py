from app.core.redis import get_redis
from app.schemas.negotiation import (
    AuthorityTier,
    BuyerSignals,
    DecisionType,
)
from app.services.decision_controller import (
    NegotiationDecisionController,
)


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


def test_high_trust_request_produces_strategic_counter():
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

    assert result.decision == DecisionType.COUNTER
    assert result.authority == AuthorityTier.FULL

    # Seller does not automatically grant buyer's request.
    assert 0 < result.discount_pct < 10

    # Hard merchant ceiling.
    assert result.discount_pct <= 12

    # Margin protection.
    assert result.final_price >= 7000

    # Opening offer reserves budget because this direct NDC call
    # uses the default reserve_budget=True.
    assert result.budget_remaining == (
        5000 - result.discount_value
    )


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

    assert result.decision == DecisionType.COUNTER

    # Seller's actual concession is below buyer's request.
    assert result.discount_pct < 30

    # Seller can never cross the merchant ceiling.
    assert result.discount_pct <= 12

    assert result.final_price >= 7000


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

    assert result.discount_value <= 500
    assert result.discount_value >= 0
    assert result.budget_remaining >= 0

    assert result.final_price >= 7000
    assert result.discount_pct <= 10
    assert result.discount_pct <= 12


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


def test_offer_never_falls_below_product_cost():
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
    assert result.discount_value <= 500
    assert result.discount_pct <= 5


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

    assert result.decision == DecisionType.COUNTER

    assert 0 < result.discount_pct < 10
    assert result.discount_value > 0
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

    assert result.budget_remaining == 5000

    reservation = controller.commit_offer(
        merchant_id="commit",
        period="test",
        discount_value=result.discount_value,
    )

    assert reservation.allowed is True
    assert reservation.remaining == (
        5000 - result.discount_value
    )


def test_restricted_trust_requires_restriction():
    controller = make_controller()

    result = controller.decide(
        merchant_id="restricted",
        period="test",
        buyer_signals=make_signals(
            identity=70,
            intent=70,
            history=70,
            violations=0,
            behavior=70,
        ),
        product_price=10000,
        product_cost=7000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=5000,
    )

    assert result.authority == AuthorityTier.RESTRICTED
    assert result.decision == DecisionType.RESTRICT

    # Restriction does not bypass economic safety.
    assert result.discount_pct <= 10
    assert result.discount_pct <= 12
    assert result.final_price >= 7000


def test_budget_cannot_be_overspent_across_transactions():
    controller = make_controller()

    first = controller.decide(
        merchant_id="repeat",
        period="test",
        buyer_signals=make_signals(),
        product_price=10000,
        product_cost=7000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=1000,
    )

    assert first.discount_value <= 1000
    assert first.budget_remaining >= 0

    second = controller.decide(
        merchant_id="repeat",
        period="test",
        buyer_signals=make_signals(),
        product_price=10000,
        product_cost=7000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=1000,
    )

    # Whatever remains after the first committed offer is the
    # maximum available for the second transaction.
    assert second.discount_value <= first.budget_remaining
    assert second.budget_remaining >= 0


def test_zero_discount_does_not_create_negative_budget():
    controller = make_controller()

    result = controller.decide(
        merchant_id="zero",
        period="test",
        buyer_signals=make_signals(),
        product_price=10000,
        product_cost=7000,
        requested_discount_pct=0,
        max_discount_pct=12,
        allocated_budget=5000,
    )

    assert result.discount_value == 0
    assert result.discount_pct == 0
    assert result.final_price == 10000
    assert result.budget_remaining == 5000


def test_ndc_rejects_unsafe_offer_engine_output():
    controller = make_controller()

    class MaliciousOfferEngine:
        def calculate(self, **kwargs):
            from app.services.offer_engine import OfferResult

            return OfferResult(
                discount_pct=50.0,
                discount_value=5000.0,
                final_price=5000.0,
                reason="Unsafe optimizer output",
            )

    controller.offer_engine = MaliciousOfferEngine()

    result = controller.decide(
        merchant_id="adversarial",
        period="test",
        buyer_signals=make_signals(),
        product_price=10000,
        product_cost=7000,
        requested_discount_pct=10,
        max_discount_pct=12,
        allocated_budget=5000,
    )

    assert result.decision == DecisionType.RESTRICT
    assert result.discount_pct == 0
    assert result.discount_value == 0
    assert result.final_price == 10000
    assert (
        "exceeded merchant discount ceiling"
        in result.reason
    )
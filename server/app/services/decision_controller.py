from dataclasses import dataclass

from app.schemas.negotiation import (
    AuthorityTier,
    BuyerSignals,
    DecisionType,
)
from app.services.bounds import BoundsEngine
from app.services.budget import AutonomyBudgetManager
from app.services.offer_engine import DynamicOfferEngine
from app.services.trust_score import TrustScoreEngine


@dataclass(frozen=True)
class NDCResult:
    decision: DecisionType
    authority: AuthorityTier
    trust_score: float
    discount_pct: float
    discount_value: float
    final_price: float
    budget_remaining: float
    reason: str


class NegotiationDecisionController:
    """
    Final authority for negotiation decisions.

    Order:
        1. Trust
        2. Bounds
        3. Budget
        4. Offer
        5. Final safety validation
        6. Optional budget reservation

    Important policy behavior:

    - Trust BLOCK -> BLOCK immediately.
    - Hard bounds violation -> BLOCK immediately.
    - Request above merchant discount ceiling -> allow negotiation
      to continue so the offer engine can produce a capped COUNTER.
    - Restricted trust -> RESTRICT.
    - Offer meeting the buyer request -> APPROVE.
    - Offer below the buyer request -> COUNTER.
    - Final offers can never exceed the merchant ceiling,
      fall below product cost, or exceed the autonomy budget.
    """

    def __init__(self, redis_client):
        self.trust_engine = TrustScoreEngine()
        self.bounds_engine = BoundsEngine()
        self.offer_engine = DynamicOfferEngine()
        self.budget_manager = AutonomyBudgetManager(redis_client)

    def decide(
        self,
        *,
        merchant_id: str,
        period: str,
        buyer_signals: BuyerSignals,
        product_price: float,
        product_cost: float,
        requested_discount_pct: float,
        max_discount_pct: float,
        allocated_budget: float,
        reserve_budget: bool = True,
        round_number: int = 1,
        previous_discount_pct: float | None = None,
        inventory: int | None = None,
    ) -> NDCResult:

        # ---------------------------------------------------------
        # 1. TRUST
        # ---------------------------------------------------------
        trust = self.trust_engine.score(buyer_signals)

        if trust.authority == AuthorityTier.BLOCK:
            return NDCResult(
                decision=DecisionType.BLOCK,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=self.budget_manager.remaining(
                    merchant_id=merchant_id,
                    period=period,
                ),
                reason=(
                    "Buyer trust score is below "
                    "the minimum threshold"
                ),
            )

        # ---------------------------------------------------------
        # 2. MERCHANT BOUNDS
        # ---------------------------------------------------------
        bounds = self.bounds_engine.evaluate(
            requested_discount_pct=requested_discount_pct,
            max_discount_pct=max_discount_pct,
            violation_count=buyer_signals.violation_count,
        )

        # Hard policy violations remain BLOCK.
        if bounds.blocked:
            return NDCResult(
                decision=DecisionType.BLOCK,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=self.budget_manager.remaining(
                    merchant_id=merchant_id,
                    period=period,
                ),
                reason=bounds.reason,
            )

        # IMPORTANT:
        #
        # bounds.allowed == False does NOT necessarily mean BLOCK.
        #
        # In particular, requesting more than the merchant's
        # discount ceiling should produce a capped seller offer
        # and therefore a COUNTER, not an immediate RESTRICT.
        #
        # We intentionally continue here.

        # ---------------------------------------------------------
        # 3. AUTONOMY BUDGET
        # ---------------------------------------------------------
        self.budget_manager.initialize(
            merchant_id=merchant_id,
            period=period,
            allocated=allocated_budget,
        )

        remaining_budget = self.budget_manager.remaining(
            merchant_id=merchant_id,
            period=period,
        )

        if remaining_budget <= 0:
            return NDCResult(
                decision=DecisionType.RESTRICT,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=0.0,
                reason="No autonomy budget remains",
            )

        # ---------------------------------------------------------
        # 4. OFFER ENGINE
        # ---------------------------------------------------------
        offer = self.offer_engine.calculate(
            product_price=product_price,
            product_cost=product_cost,
            requested_discount_pct=requested_discount_pct,
            max_discount_pct=bounds.max_discount_pct,
            remaining_budget=remaining_budget,
            round_number=round_number,
            previous_discount_pct=previous_discount_pct,
            inventory=inventory,
        )

        # ---------------------------------------------------------
        # 5. FINAL SAFETY VALIDATION
        # ---------------------------------------------------------

        # The offer engine must never produce a discount above
        # the merchant's hard ceiling.
        if offer.discount_pct > bounds.max_discount_pct:
            return NDCResult(
                decision=DecisionType.RESTRICT,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=remaining_budget,
                reason=(
                    "Final offer exceeded merchant "
                    "discount ceiling"
                ),
            )

        # Never sell below product cost.
        if offer.final_price < product_cost:
            return NDCResult(
                decision=DecisionType.RESTRICT,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=remaining_budget,
                reason=(
                    "Final offer would fall below "
                    "product cost"
                ),
            )

        # Never spend more autonomy budget than remains.
        if offer.discount_value > remaining_budget:
            return NDCResult(
                decision=DecisionType.RESTRICT,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=offer.discount_pct,
                discount_value=offer.discount_value,
                final_price=offer.final_price,
                budget_remaining=remaining_budget,
                reason=(
                    "Requested discount exceeds the "
                    "remaining autonomy budget"
                ),
            )

        # ---------------------------------------------------------
        # 6. DECISION
        # ---------------------------------------------------------

        if trust.authority == AuthorityTier.RESTRICTED:
            decision = DecisionType.RESTRICT

        elif offer.discount_pct >= requested_discount_pct:
            decision = DecisionType.APPROVE

        else:
            # The seller cannot satisfy the buyer's requested
            # discount. Continue negotiation with a counter-offer.
            decision = DecisionType.COUNTER

        # ---------------------------------------------------------
        # 7. OPTIONAL BUDGET RESERVATION
        # ---------------------------------------------------------
        if reserve_budget:
            reservation = self.budget_manager.reserve(
                merchant_id=merchant_id,
                period=period,
                discount_value=offer.discount_value,
            )

            if not reservation.allowed:
                return NDCResult(
                    decision=DecisionType.RESTRICT,
                    authority=trust.authority,
                    trust_score=trust.score,
                    discount_pct=0.0,
                    discount_value=0.0,
                    final_price=product_price,
                    budget_remaining=reservation.remaining,
                    reason=reservation.reason,
                )

            budget_remaining = reservation.remaining
        else:
            budget_remaining = remaining_budget

        return NDCResult(
            decision=decision,
            authority=trust.authority,
            trust_score=trust.score,
            discount_pct=offer.discount_pct,
            discount_value=offer.discount_value,
            final_price=offer.final_price,
            budget_remaining=budget_remaining,
            reason=offer.reason,
        )

    def commit_offer(
        self,
        *,
        merchant_id: str,
        period: str,
        discount_value: float,
    ):
        return self.budget_manager.reserve(
            merchant_id=merchant_id,
            period=period,
            discount_value=discount_value,
        )

    def authorize_accepted_offer(
        self,
        *,
        merchant_id: str,
        period: str,
        buyer_signals: BuyerSignals,
        product_price: float,
        product_cost: float,
        discount_pct: float,
        max_discount_pct: float,
        allocated_budget: float,
    ) -> NDCResult:

        # ---------------------------------------------------------
        # 1. TRUST
        # ---------------------------------------------------------
        trust = self.trust_engine.score(buyer_signals)

        if trust.authority == AuthorityTier.BLOCK:
            return NDCResult(
                decision=DecisionType.BLOCK,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=self.budget_manager.remaining(
                    merchant_id=merchant_id,
                    period=period,
                ),
                reason=(
                    "Buyer trust score is below "
                    "the minimum threshold"
                ),
            )

        # ---------------------------------------------------------
        # 2. MERCHANT BOUNDS
        # ---------------------------------------------------------
        bounds = self.bounds_engine.evaluate(
            requested_discount_pct=discount_pct,
            max_discount_pct=max_discount_pct,
            violation_count=buyer_signals.violation_count,
        )

        if bounds.blocked:
            return NDCResult(
                decision=DecisionType.BLOCK,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=self.budget_manager.remaining(
                    merchant_id=merchant_id,
                    period=period,
                ),
                reason=bounds.reason,
            )

        # Unlike the negotiation phase, an accepted offer is
        # attempting to become a real transaction.
        #
        # Therefore an accepted discount above the merchant
        # ceiling cannot be authorized.
        if not bounds.allowed:
            return NDCResult(
                decision=DecisionType.RESTRICT,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=self.budget_manager.remaining(
                    merchant_id=merchant_id,
                    period=period,
                ),
                reason=(
                    "Accepted offer is outside "
                    "merchant policy bounds"
                ),
            )

        # ---------------------------------------------------------
        # 3. AUTONOMY BUDGET
        # ---------------------------------------------------------
        self.budget_manager.initialize(
            merchant_id=merchant_id,
            period=period,
            allocated=allocated_budget,
        )

        remaining_budget = self.budget_manager.remaining(
            merchant_id=merchant_id,
            period=period,
        )

        discount_value = round(
            product_price * discount_pct / 100,
            2,
        )

        final_price = round(
            product_price - discount_value,
            2,
        )

        if remaining_budget <= 0:
            return NDCResult(
                decision=DecisionType.RESTRICT,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=0.0,
                reason="No autonomy budget remains",
            )

        if discount_value > remaining_budget:
            return NDCResult(
                decision=DecisionType.RESTRICT,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=discount_pct,
                discount_value=discount_value,
                final_price=final_price,
                budget_remaining=remaining_budget,
                reason=(
                    "Insufficient autonomy budget "
                    "for accepted offer"
                ),
            )

        # ---------------------------------------------------------
        # 4. COST SAFETY
        # ---------------------------------------------------------
        if final_price < product_cost:
            return NDCResult(
                decision=DecisionType.RESTRICT,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=remaining_budget,
                reason=(
                    "Accepted offer would fall "
                    "below product cost"
                ),
            )

        # ---------------------------------------------------------
        # 5. AUTHORITY SAFETY
        # ---------------------------------------------------------
        if trust.authority == AuthorityTier.RESTRICTED:
            return NDCResult(
                decision=DecisionType.RESTRICT,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=remaining_budget,
                reason=(
                    "Buyer authority level does not "
                    "permit autonomous approval"
                ),
            )

        # ---------------------------------------------------------
        # 6. ATOMIC BUDGET RESERVATION
        # ---------------------------------------------------------
        reservation = self.budget_manager.reserve(
            merchant_id=merchant_id,
            period=period,
            discount_value=discount_value,
        )

        if not reservation.allowed:
            return NDCResult(
                decision=DecisionType.RESTRICT,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=reservation.remaining,
                reason=reservation.reason,
            )

        return NDCResult(
            decision=DecisionType.APPROVE,
            authority=trust.authority,
            trust_score=trust.score,
            discount_pct=discount_pct,
            discount_value=discount_value,
            final_price=final_price,
            budget_remaining=reservation.remaining,
            reason="Buyer accepted the authorized seller offer",
        )
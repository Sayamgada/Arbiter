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

    The offer engine is never allowed to override hard constraints.

    Budget reservation can be deferred for multi-round negotiations.
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
                reason="Buyer trust score is below the minimum threshold",
            )

        # ---------------------------------------------------------
        # 2. BOUNDS
        # ---------------------------------------------------------
        bounds = self.bounds_engine.evaluate(
            requested_discount_pct=requested_discount_pct,
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

        # ---------------------------------------------------------
        # 3. BUDGET
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
        # 4. OFFER
        # ---------------------------------------------------------
        offer = self.offer_engine.calculate(
            product_price=product_price,
            product_cost=product_cost,
            requested_discount_pct=requested_discount_pct,
            max_discount_pct=bounds.max_discount_pct,
            remaining_budget=remaining_budget,
        )

        # ---------------------------------------------------------
        # 5. FINAL SAFETY VALIDATION
        # ---------------------------------------------------------
        if offer.discount_pct > bounds.max_discount_pct:
            return NDCResult(
                decision=DecisionType.RESTRICT,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=remaining_budget,
                reason="Final offer exceeded merchant discount ceiling",
            )

        if offer.final_price < product_cost:
            return NDCResult(
                decision=DecisionType.RESTRICT,
                authority=trust.authority,
                trust_score=trust.score,
                discount_pct=0.0,
                discount_value=0.0,
                final_price=product_price,
                budget_remaining=remaining_budget,
                reason="Final offer would fall below product cost",
            )

        # ---------------------------------------------------------
        # 6. FINAL DECISION
        # ---------------------------------------------------------
        if trust.authority == AuthorityTier.RESTRICTED:
            decision = DecisionType.RESTRICT
        elif offer.discount_pct > 0:
            decision = DecisionType.APPROVE
        else:
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
        """
        Commit an already-authorized offer to the autonomy budget.

        Used when a buyer accepts an offer after one or more
        negotiation rounds.
        """
        return self.budget_manager.reserve(
            merchant_id=merchant_id,
            period=period,
            discount_value=discount_value,
        )
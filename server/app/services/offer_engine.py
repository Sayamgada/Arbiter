from dataclasses import dataclass


@dataclass(frozen=True)
class OfferResult:
    discount_pct: float
    discount_value: float
    final_price: float
    reason: str


class DynamicOfferEngine:
    """
    Generates the seller's strategic negotiation offer.

    The buyer's requested discount is NOT automatically granted.

    The merchant's max_discount_pct is an absolute hard ceiling.
    The engine determines the seller's actual concession beneath
    that ceiling.

    The engine considers:
    - buyer's current request
    - seller's previous concession
    - product margin
    - inventory pressure
    - negotiation round
    - remaining autonomy budget

    This engine does not make trust or authorization decisions.
    """

    def calculate(
        self,
        *,
        product_price: float,
        product_cost: float,
        requested_discount_pct: float,
        max_discount_pct: float,
        remaining_budget: float,
        round_number: int = 1,
        previous_discount_pct: float | None = None,
        inventory: int | None = None,
    ) -> OfferResult:

        if product_price <= 0:
            raise ValueError(
                "Product price must be positive"
            )

        if product_cost < 0:
            raise ValueError(
                "Product cost cannot be negative"
            )

        if product_cost > product_price:
            raise ValueError(
                "Product cost cannot exceed product price"
            )

        if not 0 <= max_discount_pct <= 100:
            raise ValueError(
                "Merchant discount ceiling must be between 0 and 100"
            )

        if requested_discount_pct < 0:
            raise ValueError(
                "Requested discount cannot be negative"
            )

        if round_number < 1:
            raise ValueError(
                "Round number must be at least 1"
            )

        remaining_budget = max(
            remaining_budget,
            0.0,
        )

        # ---------------------------------------------------------
        # ECONOMIC CEILING
        # ---------------------------------------------------------
        #
        # Even if merchant policy permits a larger discount,
        # never discount below product cost.
        #
        margin_ceiling_pct = (
            (product_price - product_cost)
            / product_price
            * 100
        )

        economic_ceiling_pct = min(
            max_discount_pct,
            margin_ceiling_pct,
        )

        # ---------------------------------------------------------
        # BUYER REQUEST
        # ---------------------------------------------------------
        #
        # Keep the original request intact for negotiation.
        #
        buyer_request = max(
            requested_discount_pct,
            0.0,
        )

        # The seller can never promise more than its authorized
        # economic position.
        seller_target = min(
            buyer_request,
            economic_ceiling_pct,
        )

        # ---------------------------------------------------------
        # SELLER CONCESSION
        # ---------------------------------------------------------
        if seller_target <= 0:
            discount_pct = 0.0

        elif previous_discount_pct is None:
            # Opening offer deliberately leaves negotiation room.
            opening_factor = self._opening_factor(
                product_price=product_price,
                product_cost=product_cost,
                inventory=inventory,
            )

            discount_pct = (
                seller_target * opening_factor
            )

        else:
            previous = min(
                max(previous_discount_pct, 0.0),
                economic_ceiling_pct,
            )

            if seller_target <= previous:
                # Buyer has not given the seller a reason to concede
                # more. Hold the current position.
                discount_pct = previous

            else:
                gap = seller_target - previous

                # Seller becomes somewhat more flexible as rounds
                # progress, but never jumps directly to the buyer's
                # target.
                movement_factor = min(
                    0.30 + (
                        (round_number - 1) * 0.08
                    ),
                    0.55,
                )

                discount_pct = (
                    previous
                    + gap * movement_factor
                )

        # ---------------------------------------------------------
        # HARD SAFETY LIMITS
        # ---------------------------------------------------------
        discount_pct = max(
            discount_pct,
            0.0,
        )

        discount_pct = min(
            discount_pct,
            seller_target,
            economic_ceiling_pct,
            max_discount_pct,
        )

        # ---------------------------------------------------------
        # BUDGET LIMIT
        # ---------------------------------------------------------
        discount_value = (
            product_price
            * discount_pct
            / 100
        )

        discount_value = min(
            discount_value,
            remaining_budget,
        )

        final_price = (
            product_price
            - discount_value
        )

        # ---------------------------------------------------------
        # FINAL COST PROTECTION
        # ---------------------------------------------------------
        if final_price < product_cost:
            discount_value = min(
                max(
                    product_price - product_cost,
                    0.0,
                ),
                remaining_budget,
            )

            final_price = (
                product_price
                - discount_value
            )

        discount_pct = (
            discount_value
            / product_price
            * 100
        )

        discount_pct = round(
            discount_pct,
            2,
        )

        discount_value = round(
            discount_value,
            2,
        )

        final_price = round(
            final_price,
            2,
        )

        # ---------------------------------------------------------
        # REASONING
        # ---------------------------------------------------------
        if previous_discount_pct is None:
            reason = (
                "Seller opened with a strategic concession "
                "while retaining negotiation room"
            )

        elif discount_pct > previous_discount_pct:
            reason = (
                "Seller increased its concession toward the "
                "buyer's improved position"
            )

        else:
            reason = (
                "Seller maintained its concession because "
                "further movement was not justified"
            )

        return OfferResult(
            discount_pct=discount_pct,
            discount_value=discount_value,
            final_price=final_price,
            reason=reason,
        )

    @staticmethod
    def _opening_factor(
        *,
        product_price: float,
        product_cost: float,
        inventory: int | None,
    ) -> float:
        """
        Determine the seller's opening aggressiveness.

        Higher margin and healthy inventory permit a somewhat
        stronger opening concession.

        Low margin or scarce inventory produces a more defensive
        opening position.
        """

        margin_pct = (
            (product_price - product_cost)
            / product_price
            * 100
        )

        factor = 0.45

        # Margin influence.
        if margin_pct >= 35:
            factor += 0.10

        elif margin_pct < 20:
            factor -= 0.10

        # Inventory influence.
        if inventory is not None:
            if inventory <= 5:
                factor -= 0.10

            elif inventory >= 20:
                factor += 0.05

        return max(
            min(factor, 0.65),
            0.25,
        )
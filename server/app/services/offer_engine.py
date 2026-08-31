from dataclasses import dataclass


@dataclass(frozen=True)
class OfferResult:
    discount_pct: float
    discount_value: float
    final_price: float
    reason: str


class DynamicOfferEngine:
    """
    Chooses an offer within the limits supplied by the controller.

    This engine does NOT own safety constraints. It receives the
    maximum allowed discount and budget available from the controller.
    """

    def calculate(
        self,
        *,
        product_price: float,
        product_cost: float,
        requested_discount_pct: float,
        max_discount_pct: float,
        remaining_budget: float,
    ) -> OfferResult:

        if product_price <= 0:
            raise ValueError("Product price must be positive")

        if product_cost < 0:
            raise ValueError("Product cost cannot be negative")

        # Never exceed the merchant ceiling.
        discount_pct = min(
            max(requested_discount_pct, 0.0),
            max_discount_pct,
        )

        # Protect merchant margin.
        minimum_price = product_cost

        requested_discount_value = (
            product_price * discount_pct / 100
        )

        # Budget can further restrict the discount.
        discount_value = min(
            requested_discount_value,
            max(remaining_budget, 0.0),
        )

        final_price = product_price - discount_value

        # Never sell below cost.
        if final_price < minimum_price:
            discount_value = max(
                product_price - minimum_price,
                0.0,
            )

            discount_value = min(
                discount_value,
                max(remaining_budget, 0.0),
            )

            final_price = product_price - discount_value

        discount_pct = (
            discount_value / product_price * 100
        )

        return OfferResult(
            discount_pct=round(discount_pct, 2),
            discount_value=round(discount_value, 2),
            final_price=round(final_price, 2),
            reason="Offer optimized within merchant constraints",
        )

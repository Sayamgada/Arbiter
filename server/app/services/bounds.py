from dataclasses import dataclass


@dataclass(frozen=True)
class BoundsResult:
    allowed: bool
    blocked: bool
    max_discount_pct: float
    reason: str


class BoundsEngine:
    """
    Deterministic hard-safety layer.

    The merchant's configured max_discount_pct is an absolute
    ceiling. No optimizer or trust signal can increase it.
    """

    def evaluate(
        self,
        *,
        requested_discount_pct: float,
        max_discount_pct: float,
        violation_count: int = 0,
        max_violations: int = 5,
    ) -> BoundsResult:

        # Invalid configuration is itself a safety failure.
        if max_discount_pct < 0 or max_discount_pct > 100:
            return BoundsResult(
                allowed=False,
                blocked=True,
                max_discount_pct=0.0,
                reason="Invalid merchant discount ceiling",
            )

        # Never permit a negative discount request.
        if requested_discount_pct < 0:
            return BoundsResult(
                allowed=False,
                blocked=True,
                max_discount_pct=max_discount_pct,
                reason="Invalid negative discount request",
            )

        # Repeated policy violations trigger a hard block.
        if violation_count >= max_violations:
            return BoundsResult(
                allowed=False,
                blocked=True,
                max_discount_pct=max_discount_pct,
                reason="Policy violation threshold exceeded",
            )

        # Requested discount exceeds the merchant's hard ceiling.
        if requested_discount_pct > max_discount_pct:
            return BoundsResult(
                allowed=False,
                blocked=False,
                max_discount_pct=max_discount_pct,
                reason=(
                    f"Requested discount {requested_discount_pct}% "
                    f"exceeds merchant ceiling {max_discount_pct}%"
                ),
            )

        return BoundsResult(
            allowed=True,
            blocked=False,
            max_discount_pct=max_discount_pct,
            reason="Offer is within merchant policy bounds",
        )

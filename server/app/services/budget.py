from dataclasses import dataclass

from redis import Redis


@dataclass(frozen=True)
class BudgetResult:
    allowed: bool
    remaining: float
    requested_value: float
    reason: str


class AutonomyBudgetManager:
    KEY_PREFIX = "arbiter:budget:"

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def _key(self, merchant_id: str, period: str) -> str:
        return f"{self.KEY_PREFIX}{merchant_id}:{period}"

    def initialize(
        self,
        *,
        merchant_id: str,
        period: str,
        allocated: float,
    ) -> float:
        if allocated < 0:
            raise ValueError("Budget allocation cannot be negative")

        key = self._key(merchant_id, period)
        self.redis.setnx(key, allocated)

        return float(self.redis.get(key))

    def remaining(
        self,
        *,
        merchant_id: str,
        period: str,
    ) -> float:
        value = self.redis.get(self._key(merchant_id, period))
        return float(value) if value is not None else 0.0

    def reserve(
        self,
        *,
        merchant_id: str,
        period: str,
        discount_value: float,
    ) -> BudgetResult:
        if discount_value < 0:
            raise ValueError("Discount value cannot be negative")

        key = self._key(merchant_id, period)

        # Atomic Lua operation:
        # only decrement if enough budget remains.
        script = """
        local current = tonumber(redis.call('GET', KEYS[1]) or '0')
        local amount = tonumber(ARGV[1])

        if current < amount then
            return {-1, current}
        end

        local remaining = redis.call('INCRBYFLOAT', KEYS[1], -amount)
        return {1, remaining}
        """

        result = self.redis.eval(
            script,
            1,
            key,
            discount_value,
        )

        allowed = int(result[0]) == 1
        remaining = float(result[1])

        if not allowed:
            return BudgetResult(
                allowed=False,
                remaining=remaining,
                requested_value=discount_value,
                reason="Insufficient autonomy budget",
            )

        return BudgetResult(
            allowed=True,
            remaining=remaining,
            requested_value=discount_value,
            reason="Budget reserved successfully",
        )

from dataclasses import dataclass

from app.schemas.negotiation import BuyerSignals


@dataclass(frozen=True)
class DemoScenario:
    id: str
    title: str
    description: str
    buyer_signals: BuyerSignals
    requested_discount_pct: float
    max_rounds: int = 5

    # Optional scenario-specific merchant conditions.
    allocated_budget: float | None = None
    inventory: int | None = None


DEMO_SCENARIOS: dict[str, DemoScenario] = {
    "trusted-buyer": DemoScenario(
        id="trusted-buyer",
        title="Trusted Buyer",
        description=(
            "A high-trust buyer receives full autonomous "
            "negotiation authority."
        ),
        buyer_signals=BuyerSignals(
            identity_confidence=100.0,
            intent_confidence=100.0,
            history_score=100.0,
            violation_count=0,
            behavior_score=100.0,
        ),
        requested_discount_pct=10.0,
    ),

    "restricted-buyer": DemoScenario(
        id="restricted-buyer",
        title="Restricted Buyer",
        description=(
            "A medium-trust buyer receives restricted "
            "negotiation authority."
        ),
        buyer_signals=BuyerSignals(
            identity_confidence=65.0,
            intent_confidence=65.0,
            history_score=65.0,
            violation_count=0,
            behavior_score=65.0,
        ),
        requested_discount_pct=10.0,
    ),

    "untrusted-buyer": DemoScenario(
        id="untrusted-buyer",
        title="Untrusted Buyer",
        description=(
            "A low-trust buyer is blocked from autonomous "
            "negotiation."
        ),
        buyer_signals=BuyerSignals(
            identity_confidence=20.0,
            intent_confidence=20.0,
            history_score=20.0,
            violation_count=4,
            behavior_score=20.0,
        ),
        requested_discount_pct=10.0,
    ),

    "budget-constraint": DemoScenario(
        id="budget-constraint",
        title="Budget Constraint",
        description=(
            "The merchant has very little remaining "
            "negotiation budget."
        ),
        buyer_signals=BuyerSignals(
            identity_confidence=100.0,
            intent_confidence=100.0,
            history_score=100.0,
            violation_count=0,
            behavior_score=100.0,
        ),
        requested_discount_pct=10.0,
        allocated_budget=100.0,
    ),

    "inventory-pressure": DemoScenario(
        id="inventory-pressure",
        title="Inventory Pressure",
        description=(
            "The product has critically low inventory."
        ),
        buyer_signals=BuyerSignals(
            identity_confidence=100.0,
            intent_confidence=100.0,
            history_score=100.0,
            violation_count=0,
            behavior_score=100.0,
        ),
        requested_discount_pct=10.0,
        inventory=1,
    ),

    "policy-boundary": DemoScenario(
        id="policy-boundary",
        title="Policy Boundary",
        description=(
            "The buyer requests a discount beyond the "
            "merchant's allowed ceiling."
        ),
        buyer_signals=BuyerSignals(
            identity_confidence=100,
            intent_confidence=100,
            history_score=100,
            violation_count=0,
            behavior_score=100,
        ),
        requested_discount_pct=15,
    ),

    "multi-round": DemoScenario(
        id="multi-round",
        title="Multi-round Negotiation",
        description=(
            "Buyer and seller exchange multiple offers "
            "before reaching a decision."
        ),
        buyer_signals=BuyerSignals(
            identity_confidence=100.0,
            intent_confidence=100.0,
            history_score=100.0,
            violation_count=0,
            behavior_score=100.0,
        ),
        requested_discount_pct=10.0,
        max_rounds=5,
    ),

    "final-authorization": DemoScenario(
        id="final-authorization",
        title="Final Authorization",
        description=(
            "An accepted offer proceeds through deterministic "
            "transaction authorization."
        ),
        buyer_signals=BuyerSignals(
            identity_confidence=100.0,
            intent_confidence=100.0,
            history_score=100.0,
            violation_count=0,
            behavior_score=100.0,
        ),
        requested_discount_pct=5.0,
    ),
}


def get_demo_scenario(
    scenario_id: str,
) -> DemoScenario | None:
    return DEMO_SCENARIOS.get(scenario_id)


def list_demo_scenarios() -> list[DemoScenario]:
    return list(DEMO_SCENARIOS.values())
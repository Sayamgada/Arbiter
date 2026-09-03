export type ScenarioId =
  | "trusted-buyer"
  | "restricted-buyer"
  | "untrusted-buyer"
  | "budget-constraint"
  | "inventory-pressure"
  | "policy-boundary"
  | "multi-round"
  | "final-authorization";

export type ScenarioIcon =
  | "shield-check"
  | "shield-alert"
  | "shield-x"
  | "wallet"
  | "package"
  | "scale"
  | "repeat"
  | "lock-check";

export type BuyerSignals = {
  identity_confidence: number;
  intent_confidence: number;
  history_score: number;
  violation_count: number;
  behavior_score: number;
};

export type Scenario = {
  id: ScenarioId;
  icon: ScenarioIcon;
  title: string;
  shortTitle: string;
  description: string;
  demonstration: string;
  buyerSignals: BuyerSignals;
  requestedDiscountPct: number;
  allocatedBudget?: number;
  inventory?: number;
};

const trustedSignals: BuyerSignals = {
  identity_confidence: 100,
  intent_confidence: 100,
  history_score: 100,
  violation_count: 0,
  behavior_score: 100,
};

const restrictedSignals: BuyerSignals = {
  identity_confidence: 65,
  intent_confidence: 65,
  history_score: 65,
  violation_count: 0,
  behavior_score: 65,
};

const untrustedSignals: BuyerSignals = {
  identity_confidence: 20,
  intent_confidence: 20,
  history_score: 20,
  violation_count: 4,
  behavior_score: 20,
};

export const scenarios: Scenario[] = [
  {
    id: "trusted-buyer",
    icon: "shield-check",
    title: "Trusted Buyer",
    shortTitle: "Trusted",
    description:
      "A high-confidence buyer receives full autonomous negotiation authority.",
    demonstration:
      "Demonstrates full autonomy for a highly trusted buyer.",
    buyerSignals: trustedSignals,
    requestedDiscountPct: 10,
  },

  {
    id: "restricted-buyer",
    icon: "shield-alert",
    title: "Restricted Buyer",
    shortTitle: "Restricted",
    description:
      "A moderately trusted buyer can negotiate, but sensitive decisions require restriction.",
    demonstration:
      "Demonstrates restricted autonomy when trust falls into the middle tier.",
    buyerSignals: restrictedSignals,
    requestedDiscountPct: 10,
  },

  {
    id: "untrusted-buyer",
    icon: "shield-x",
    title: "Untrusted Buyer",
    shortTitle: "Untrusted",
    description:
      "A low-trust buyer is blocked from autonomous commerce.",
    demonstration:
      "Demonstrates deterministic blocking for insufficient trust.",
    buyerSignals: untrustedSignals,
    requestedDiscountPct: 10,
  },

  {
    id: "budget-constraint",
    icon: "wallet",
    title: "Budget Constraint",
    shortTitle: "Budget",
    description:
      "Negotiation operates under a deliberately constrained autonomy budget.",
    demonstration:
      "Demonstrates budget-aware negotiation and reservation limits.",
    buyerSignals: trustedSignals,
    requestedDiscountPct: 10,
    allocatedBudget: 100,
  },

  {
    id: "inventory-pressure",
    icon: "package",
    title: "Inventory Pressure",
    shortTitle: "Inventory",
    description:
      "Low inventory causes the seller to become more conservative.",
    demonstration:
      "Demonstrates inventory-aware offer behavior.",
    buyerSignals: trustedSignals,
    requestedDiscountPct: 10,
    inventory: 1,
  },

  {
    id: "policy-boundary",
    icon: "scale",
    title: "Policy Boundary",
    shortTitle: "Policy",
    description:
      "A buyer requests a discount above the merchant's allowed ceiling.",
    demonstration:
      "Demonstrates deterministic enforcement of merchant discount policy.",
    buyerSignals: trustedSignals,
    requestedDiscountPct: 15,
  },

  {
    id: "multi-round",
    icon: "repeat",
    title: "Multi-Round Negotiation",
    shortTitle: "Multi-Round",
    description:
      "Buyer and seller progressively negotiate toward an authorized offer.",
    demonstration:
      "Demonstrates stateful multi-round negotiation without exceeding policy.",
    buyerSignals: trustedSignals,
    requestedDiscountPct: 10,
  },

  {
    id: "final-authorization",
    icon: "lock-check",
    title: "Final Authorization",
    shortTitle: "Authorization",
    description:
      "An accepted offer passes through a separate final transaction authorization gate.",
    demonstration:
      "Demonstrates the separate authorization boundary between negotiation and payment.",
    buyerSignals: trustedSignals,
    requestedDiscountPct: 5,
  },
];

export function getScenario(
  id: string,
): Scenario | undefined {
  return scenarios.find(
    (scenario) => scenario.id === id,
  );
}
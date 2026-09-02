export type ScenarioId =
  | "trusted-buyer"
  | "restricted-buyer"
  | "untrusted-buyer"
  | "budget-constraint"
  | "inventory-pressure"
  | "policy-boundary"
  | "multi-round"
  | "final-authorization";

export type Scenario = {
  id: ScenarioId;
  icon: string;
  title: string;
  shortTitle: string;
  description: string;
  demonstration: string;
};

export const scenarios: Scenario[] = [
  {
    id: "trusted-buyer",
    icon: "🟢",
    title: "Trusted Buyer",
    shortTitle: "Full Autonomy",
    description:
      "A high-trust buyer receives autonomous negotiation authority.",
    demonstration: "Demonstrates full autonomous negotiation.",
  },
  {
    id: "restricted-buyer",
    icon: "🟡",
    title: "Restricted Buyer",
    shortTitle: "Controlled Autonomy",
    description:
      "A medium-trust buyer receives limited negotiation authority.",
    demonstration:
      "Demonstrates restricted authority and controlled concessions.",
  },
  {
    id: "untrusted-buyer",
    icon: "🔴",
    title: "Untrusted Buyer",
    shortTitle: "Trust Enforcement",
    description:
      "A low-trust buyer is prevented from negotiating autonomously.",
    demonstration:
      "Demonstrates trust-based blocking and enforcement.",
  },
  {
    id: "budget-constraint",
    icon: "💰",
    title: "Budget Constraint",
    shortTitle: "Autonomy Budget",
    description:
      "The merchant has limited remaining negotiation budget.",
    demonstration:
      "Demonstrates budget-aware discount authorization.",
  },
  {
    id: "inventory-pressure",
    icon: "📦",
    title: "Inventory Pressure",
    shortTitle: "Business Awareness",
    description:
      "Low inventory changes how aggressively the merchant negotiates.",
    demonstration:
      "Demonstrates inventory-aware business constraints.",
  },
  {
    id: "policy-boundary",
    icon: "🚫",
    title: "Policy Boundary",
    shortTitle: "Deterministic Policy",
    description:
      "The buyer requests a discount beyond the merchant's allowed ceiling.",
    demonstration:
      "Demonstrates deterministic merchant policy enforcement.",
  },
  {
    id: "multi-round",
    icon: "🤝",
    title: "Multi-round Negotiation",
    shortTitle: "Agentic Negotiation",
    description:
      "Buyer and seller agents exchange multiple counter-offers.",
    demonstration:
      "Demonstrates the agentic negotiation loop.",
  },
  {
    id: "final-authorization",
    icon: "⚡",
    title: "Final Authorization",
    shortTitle: "Transaction Control",
    description:
      "An accepted offer passes through final transaction authorization.",
    demonstration:
      "Demonstrates trust, decision, and transaction authorization.",
  },
];

export function getScenario(id: string): Scenario | undefined {
  return scenarios.find((scenario) => scenario.id === id);
}
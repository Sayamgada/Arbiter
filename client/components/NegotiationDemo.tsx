"use client";

import { useState } from "react";

import {
  getDemoContext,
  startNegotiation,
  type DemoContext,
  type NegotiationMessage,
  type NegotiationSessionResponse,
  type ScenarioId,
} from "@/lib/api";

import type { Scenario } from "@/lib/scenarios";

type Props = {
  scenario: Scenario;
};

function money(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "—";
  }

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function percentage(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "—";
  }

  return `${value.toFixed(2)}%`;
}

function messageLabel(message: NegotiationMessage) {
  switch (message.message_type) {
    case "purchase_request":
      return "BUYER REQUEST";

    case "counter_offer":
      return message.discount_value && message.discount_value > 0
        ? "SELLER COUNTER"
        : "BUYER COUNTER";

    case "offer":
      return "SELLER OFFER";

    case "accept":
      return "BUYER ACCEPTED";

    case "reject":
      return "SELLER REJECTED";

    case "final":
      return "FINAL";

    default:
      return message.message_type.replaceAll("_", " ").toUpperCase();
  }
}

function isBuyerMessage(message: NegotiationMessage) {
  return (
    message.message_type === "purchase_request" ||
    (message.message_type === "counter_offer" &&
      (!message.discount_value || message.discount_value === 0)) ||
    message.message_type === "accept"
  );
}

function StatusBadge({
  status,
}: {
  status: NegotiationSessionResponse["status"];
}) {
  const config = {
    accepted: {
      label: "AUTHORIZED",
      className:
        "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    },
    rejected: {
      label: "REJECTED",
      className:
        "border-red-500/30 bg-red-500/10 text-red-300",
    },
    blocked: {
      label: "BLOCKED",
      className:
        "border-red-500/30 bg-red-500/10 text-red-300",
    },
    expired: {
      label: "EXPIRED",
      className:
        "border-amber-500/30 bg-amber-500/10 text-amber-300",
    },
    active: {
      label: "ACTIVE",
      className:
        "border-blue-500/30 bg-blue-500/10 text-blue-300",
    },
  }[status];

  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-semibold tracking-wide ${config.className}`}
    >
      {config.label}
    </span>
  );
}

export default function NegotiationDemo({
  scenario,
}: Props) {
  const [context, setContext] = useState<DemoContext | null>(null);
  const [result, setResult] =
    useState<NegotiationSessionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runScenario() {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const demoContext = await getDemoContext();

      setContext(demoContext);

      const response = await startNegotiation(
        demoContext,
        getRequestedDiscount(scenario.id),
        scenario.id as ScenarioId,
      );

      setResult(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to execute scenario.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mt-8">
      {!result && (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-8">
          <div className="mx-auto max-w-xl text-center">
            <div className="text-5xl">{scenario.icon}</div>

            <h2 className="mt-5 text-2xl font-semibold">
              Ready to run scenario
            </h2>

            <p className="mt-3 text-sm leading-6 text-zinc-400">
              Execute the real Arbiter negotiation engine using this
              scenario&apos;s deterministic trust, policy, budget, and
              inventory configuration.
            </p>

            <button
              onClick={runScenario}
              disabled={loading}
              className="mt-7 rounded-xl bg-white px-6 py-3 text-sm font-semibold text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading
                ? "Running negotiation..."
                : "Run scenario"}
            </button>

            {error && (
              <div className="mt-5 rounded-xl border border-red-900/50 bg-red-950/20 p-4 text-left">
                <p className="text-xs font-semibold uppercase tracking-wider text-red-400">
                  Execution error
                </p>

                <p className="mt-2 text-sm text-red-200">
                  {error}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {result && context && (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            <Metric
              label="Trust Score"
              value={trustScore(context)}
            />

            <Metric
              label="Requested"
              value={percentage(
                getRequestedDiscount(scenario.id),
              )}
            />

            <Metric
              label="Rounds"
              value={String(result.rounds)}
            />

            <Metric
              label="Status"
              value={<StatusBadge status={result.status} />}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950">
              <div className="flex items-center justify-between border-b border-zinc-800 px-5 py-4">
                <div>
                  <p className="text-sm font-semibold">
                    Negotiation Transcript
                  </p>

                  <p className="mt-1 text-xs text-zinc-500">
                    {result.session_id}
                  </p>
                </div>

                <button
                  onClick={runScenario}
                  disabled={loading}
                  className="rounded-lg border border-zinc-700 px-3 py-2 text-xs font-medium text-zinc-300 transition hover:border-zinc-500 hover:text-white disabled:opacity-50"
                >
                  {loading ? "Running..." : "Run again"}
                </button>
              </div>

              <div className="max-h-[650px] space-y-3 overflow-y-auto p-5">
                {result.messages.map((message, index) => {
                  const buyer = isBuyerMessage(message);

                  return (
                    <div
                      key={`${message.round_number}-${index}`}
                      className={`flex ${
                        buyer
                          ? "justify-start"
                          : "justify-end"
                      }`}
                    >
                      <div
                        className={`max-w-[85%] rounded-2xl border p-4 ${
                          buyer
                            ? "border-zinc-800 bg-zinc-900"
                            : "border-blue-900/40 bg-blue-950/20"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-4">
                          <span
                            className={`text-[10px] font-bold tracking-[0.16em] ${
                              buyer
                                ? "text-zinc-500"
                                : "text-blue-400"
                            }`}
                          >
                            {messageLabel(message)}
                          </span>

                          <span className="text-[10px] text-zinc-600">
                            R{message.round_number}
                          </span>
                        </div>

                        <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-zinc-200">
                          {message.message}
                        </p>

                        {(message.price !== undefined ||
                          message.proposed_price !== undefined ||
                          message.discount_pct !== undefined) && (
                          <div className="mt-4 flex flex-wrap gap-2">
                            {(message.price !== undefined ||
                              message.proposed_price !==
                                undefined) && (
                              <span className="rounded-lg bg-black/30 px-2.5 py-1.5 text-xs text-zinc-300">
                                {money(
                                  message.price ??
                                    message.proposed_price,
                                )}
                              </span>
                            )}

                            {message.discount_pct !==
                              undefined && (
                              <span className="rounded-lg bg-black/30 px-2.5 py-1.5 text-xs text-zinc-300">
                                {percentage(
                                  message.discount_pct,
                                )}{" "}
                                discount
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <aside className="space-y-4">
              <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-5">
                <p className="text-xs uppercase tracking-[0.18em] text-zinc-600">
                  Final Decision
                </p>

                <div className="mt-4">
                  <StatusBadge status={result.status} />
                </div>

                <p className="mt-4 text-sm leading-6 text-zinc-300">
                  {result.message}
                </p>
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-5">
                <p className="text-xs uppercase tracking-[0.18em] text-zinc-600">
                  Transaction
                </p>

                {result.transaction_id ? (
                  <>
                    <p className="mt-3 break-all font-mono text-xs text-emerald-300">
                      {result.transaction_id}
                    </p>

                    <div className="mt-5 grid grid-cols-2 gap-3">
                      <div>
                        <p className="text-xs text-zinc-600">
                          Final price
                        </p>

                        <p className="mt-1 text-lg font-semibold">
                          {money(result.final_price)}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-zinc-600">
                          Discount
                        </p>

                        <p className="mt-1 text-lg font-semibold">
                          {percentage(
                            result.final_discount_pct,
                          )}
                        </p>
                      </div>
                    </div>
                  </>
                ) : (
                  <p className="mt-3 text-sm text-zinc-500">
                    No transaction was authorized.
                  </p>
                )}
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-5">
                <p className="text-xs uppercase tracking-[0.18em] text-zinc-600">
                  Product
                </p>

                <p className="mt-3 text-sm font-medium">
                  {context.product.name}
                </p>

                <div className="mt-4 space-y-2 text-xs">
                  <Row
                    label="Listed price"
                    value={money(context.product.price)}
                  />

                  <Row
                    label="Inventory"
                    value={String(context.product.inventory)}
                  />

                  <Row
                    label="Merchant ceiling"
                    value={percentage(
                      context.merchant.max_discount_pct,
                    )}
                  />

                  <Row
                    label="Daily budget"
                    value={money(
                      context.merchant.daily_budget,
                    )}
                  />
                </div>
              </div>
            </aside>
          </div>
        </div>
      )}
    </section>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-zinc-600">
        {label}
      </p>

      <div className="mt-2 text-lg font-semibold text-zinc-100">
        {value}
      </div>
    </div>
  );
}

function Row({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-zinc-600">{label}</span>
      <span className="text-zinc-300">{value}</span>
    </div>
  );
}

function getRequestedDiscount(
  scenarioId: ScenarioId,
): number {
  switch (scenarioId) {
    case "trusted-buyer":
      return 10;

    case "restricted-buyer":
      return 10;

    case "untrusted-buyer":
      return 10;

    case "budget-constraint":
      return 10;

    case "inventory-pressure":
      return 10;

    case "policy-boundary":
      return 15;

    case "multi-round":
      return 10;

    case "final-authorization":
      return 5;

    default:
      return 10;
  }
}

function trustScore(context: DemoContext) {
  const buyer = context.buyer;

  const violationScore =
    (1 - Math.min(buyer.violation_count / 5, 1)) * 100;

  return (
    buyer.identity_confidence * 0.3 +
    buyer.intent_confidence * 0.25 +
    buyer.history_score * 0.2 +
    violationScore * 0.15 +
    buyer.behavior_score * 0.1
  ).toFixed(0);
}
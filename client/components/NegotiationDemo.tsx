"use client";

import { useState } from "react";
import type { ReactNode } from "react";

import {
  createPaymentOrder,
  getDemoContext,
  startNegotiation,
  verifyPayment,
  type DemoContext,
  type NegotiationMessage,
  type NegotiationSessionResponse,
  type ScenarioId,
} from "@/lib/api";

import type { Scenario } from "@/lib/scenarios";

type Props = {
  scenario: Scenario;
};

/* -------------------------------------------------------------------------- */
/* Razorpay browser types                                                     */
/* -------------------------------------------------------------------------- */

declare global {
  interface Window {
    Razorpay: new (options: RazorpayOptions) => RazorpayInstance;
  }
}

type RazorpayOptions = {
  key: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  order_id: string;
  handler: (response: {
    razorpay_payment_id: string;
    razorpay_order_id: string;
    razorpay_signature: string;
  }) => void | Promise<void>;
  modal?: {
    ondismiss?: () => void;
  };
  theme?: {
    color?: string;
  };
};

type RazorpayInstance = {
  open: () => void;
};

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

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

function calculateTrust(signals: Scenario["buyerSignals"]) {
  const violationScore = (1 - Math.min(signals.violation_count / 5, 1)) * 100;

  const weighted = {
    identity: signals.identity_confidence * 0.3,
    intent: signals.intent_confidence * 0.25,
    history: signals.history_score * 0.2,
    violations: violationScore * 0.15,
    behavior: signals.behavior_score * 0.1,
  };

  const total =
    weighted.identity +
    weighted.intent +
    weighted.history +
    weighted.violations +
    weighted.behavior;

  return {
    violationScore,
    weighted,
    total,
  };
}

function getAuthority(score: number) {
  if (score >= 80) {
    return {
      label: "FULL AUTONOMY",
      className: "text-emerald-300",
      barClassName: "bg-emerald-400",
    };
  }

  if (score >= 40) {
    return {
      label: "RESTRICTED",
      className: "text-amber-300",
      barClassName: "bg-amber-400",
    };
  }

  return {
    label: "BLOCKED",
    className: "text-red-300",
    barClassName: "bg-red-400",
  };
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

/* -------------------------------------------------------------------------- */
/* Status                                                                     */
/* -------------------------------------------------------------------------- */

function StatusBadge({
  status,
}: {
  status: NegotiationSessionResponse["status"];
}) {
  const config = {
    accepted: {
      label: "NEGOTIATION ACCEPTED",
      className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    },

    rejected: {
      label: "REJECTED",
      className: "border-red-500/30 bg-red-500/10 text-red-300",
    },

    blocked: {
      label: "BLOCKED",
      className: "border-red-500/30 bg-red-500/10 text-red-300",
    },

    expired: {
      label: "EXPIRED",
      className: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    },

    active: {
      label: "ACTIVE",
      className: "border-blue-500/30 bg-blue-500/10 text-blue-300",
    },
  }[status];

  return (
    <span
      className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold tracking-wide ${config.className}`}
    >
      {config.label}
    </span>
  );
}

/* -------------------------------------------------------------------------- */
/* Main component                                                             */
/* -------------------------------------------------------------------------- */

export default function NegotiationDemo({ scenario }: Props) {
  const [result, setResult] = useState<NegotiationSessionResponse | null>(null);

  const [context, setContext] = useState<DemoContext | null>(null);

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [requestedDiscount, setRequestedDiscount] = useState(
    scenario.requestedDiscountPct,
  );

  /*
   * Trust is intentionally only exposed after negotiation begins.
   */
  const [showTrustBreakdown, setShowTrustBreakdown] = useState(false);

  /* ------------------------------------------------------------------------ */
  /* Payment state                                                            */
  /* ------------------------------------------------------------------------ */

  const [paymentState, setPaymentState] = useState<
    "idle" | "creating" | "checkout" | "verifying" | "authorized" | "failed"
  >("idle");

  const [paymentError, setPaymentError] = useState<string | null>(null);

  /* ------------------------------------------------------------------------ */
  /* Trust                                                                    */
  /* ------------------------------------------------------------------------ */

  const trust = calculateTrust(scenario.buyerSignals);

  const authority = getAuthority(trust.total);

  /* ------------------------------------------------------------------------ */
  /* Start negotiation                                                        */
  /* ------------------------------------------------------------------------ */

  async function runScenario() {
    setLoading(true);
    setError(null);
    setResult(null);

    setPaymentState("idle");
    setPaymentError(null);
    setShowTrustBreakdown(false);

    try {
      const demoContext = await getDemoContext();

      setContext(demoContext);

      const response = await startNegotiation(
        demoContext,
        requestedDiscount,
        scenario.id as ScenarioId,
      );

      setResult(response);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to execute scenario.",
      );
    } finally {
      setLoading(false);
    }
  }

  /* ------------------------------------------------------------------------ */
  /* Reset                                                                    */
  /* ------------------------------------------------------------------------ */

  function resetScenario() {
    setResult(null);
    setContext(null);

    setError(null);

    setPaymentState("idle");
    setPaymentError(null);

    setShowTrustBreakdown(false);
  }

  /* ------------------------------------------------------------------------ */
  /* Razorpay                                                                  */
  /* ------------------------------------------------------------------------ */

  async function loadRazorpay() {
    if (typeof window === "undefined") {
      throw new Error("Razorpay can only be loaded in the browser.");
    }

    if (window.Razorpay) {
      return;
    }

    await new Promise<void>((resolve, reject) => {
      const existing = document.querySelector(
        'script[src="https://checkout.razorpay.com/v1/checkout.js"]',
      );

      if (existing) {
        existing.addEventListener("load", () => resolve(), { once: true });

        existing.addEventListener(
          "error",
          () => reject(new Error("Unable to load Razorpay Checkout.")),
          { once: true },
        );

        return;
      }

      const script = document.createElement("script");

      script.src = "https://checkout.razorpay.com/v1/checkout.js";

      script.async = true;

      script.onload = () => resolve();

      script.onerror = () =>
        reject(new Error("Unable to load Razorpay Checkout."));

      document.body.appendChild(script);
    });
  }

  async function handlePayment() {
    if (!result?.transaction_id) {
      return;
    }

    const razorpayKey = process.env.RAZORPAY_KEY_ID;

    if (!razorpayKey) {
      setPaymentState("failed");

      setPaymentError("RAZORPAY_KEY_ID is not configured.");

      return;
    }

    try {
      setPaymentError(null);

      /*
       * Step 1:
       * Ask Arbiter backend to create the Razorpay order.
       */
      setPaymentState("creating");

      const order = await createPaymentOrder(result.transaction_id);

      /*
       * Step 2:
       * Load Razorpay Checkout.
       */
      await loadRazorpay();

      if (!window.Razorpay) {
        throw new Error("Razorpay Checkout is unavailable.");
      }

      /*
       * Step 3:
       * Open the real Razorpay Checkout.
       */
      setPaymentState("checkout");

      const checkout = new window.Razorpay({
        key: razorpayKey,

        amount: order.amount,

        currency: order.currency,

        name: "Arbiter",

        description: "Arbiter authorized commerce transaction",

        order_id: order.razorpay_order_id,

        handler: async (payment) => {
          try {
            /*
             * Step 4:
             * Send Razorpay's signed response
             * back to Arbiter.
             */
            setPaymentState("verifying");

            await verifyPayment(
              result.transaction_id!,
              payment.razorpay_order_id,
              payment.razorpay_payment_id,
              payment.razorpay_signature,
            );

            /*
             * Step 5:
             * Backend verification succeeded.
             */
            setPaymentState("authorized");
            setPaymentError(null);
          } catch (err) {
            setPaymentState("failed");

            setPaymentError(
              err instanceof Error
                ? err.message
                : "Payment verification failed.",
            );
          }
        },

        modal: {
          ondismiss: () => {
            /*
             * Do not mark payment as failed if
             * the user simply closes Checkout.
             */
            setPaymentState("idle");
          },
        },

        theme: {
          color: "#ffffff",
        },
      });

      checkout.open();
    } catch (err) {
      setPaymentState("failed");

      setPaymentError(
        err instanceof Error
          ? err.message
          : "Unable to start Razorpay payment.",
      );
    }
  }

  /* ------------------------------------------------------------------------ */
  /* Render                                                                   */
  /* ------------------------------------------------------------------------ */

  return (
    <section className="mt-8 space-y-6">
      {/* ================================================================== */}
      {/* PRE-NEGOTIATION SCREEN                                             */}
      {/* ================================================================== */}

      {!result && (
        <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
          {/* REQUEST EXPLANATION */}

          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
            <p className="text-xs uppercase tracking-[0.18em] text-zinc-600">
              Negotiation Control
            </p>

            <h2 className="mt-3 text-xl font-semibold text-white">
              Configure the buyer request
            </h2>

            <p className="mt-3 max-w-xl text-sm leading-6 text-zinc-400">
              Choose the discount the buyer will request. Arbiter will then
              evaluate the request against trust, merchant policy, autonomy
              budget, inventory, and product economics.
            </p>

            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <InfoBox
                label="Listed price"
                value={context ? money(context.product.price) : "₹10,000"}
              />

              <InfoBox
                label="Merchant ceiling"
                value={
                  context
                    ? percentage(context.merchant.max_discount_pct)
                    : "12.00%"
                }
              />

              <InfoBox
                label="Requested price"
                value={money(
                  context?.product.price
                    ? context.product.price * (1 - requestedDiscount / 100)
                    : 10000 * (1 - requestedDiscount / 100),
                )}
              />
            </div>
          </div>

          {/* DISCOUNT SLIDER */}

          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
            <p className="text-xs uppercase tracking-[0.18em] text-zinc-600">
              Requested Discount
            </p>

            <div className="mt-5 flex items-end justify-between">
              <div>
                <p className="text-sm text-zinc-400">
                  Buyer requested discount
                </p>

                <p className="mt-1 text-4xl font-semibold text-white">
                  {requestedDiscount}%
                </p>
              </div>

              <span className="text-xs text-zinc-600">User controlled</span>
            </div>

            <input
              type="range"
              min={0}
              max={30}
              step={1}
              value={requestedDiscount}
              onChange={(event) =>
                setRequestedDiscount(Number(event.target.value))
              }
              className="mt-7 w-full accent-white"
            />

            <div className="mt-2 flex justify-between text-[10px] text-zinc-600">
              <span>0%</span>
              <span>15%</span>
              <span>30%</span>
            </div>

            <div className="mt-5 rounded-xl border border-zinc-800 bg-black/20 p-3">
              <p className="text-xs leading-5 text-zinc-500">
                The requested discount is only the buyer's starting position.
                Arbiter's deterministic controller decides what the seller can
                actually authorize.
              </p>
            </div>

            <button
              type="button"
              onClick={runScenario}
              disabled={loading}
              className="mt-5 w-full rounded-xl bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Running negotiation..." : "Start negotiation"}
            </button>
          </div>
        </div>
      )}

      {/* ================================================================== */}
      {/* ERROR                                                              */}
      {/* ================================================================== */}

      {error && (
        <div className="rounded-xl border border-red-900/50 bg-red-950/20 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-red-400">
            Execution error
          </p>

          <p className="mt-2 text-sm text-red-200">{error}</p>
        </div>
      )}

      {/* ================================================================== */}
      {/* NEGOTIATION RESULT                                                 */}
      {/* ================================================================== */}

      {result && context && (
        <div className="space-y-6">
          {/* ---------------------------------------------------------------- */}
          {/* RESULT SUMMARY                                                   */}
          {/* ---------------------------------------------------------------- */}

          <div className="grid gap-4 md:grid-cols-4">
            {/* TRUST */}

            <div className="relative rounded-xl border border-zinc-800 bg-zinc-950 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-zinc-600">
                Trust Score
              </p>

              <div className="mt-2 flex items-center gap-2">
                <span className="text-2xl font-semibold text-white">
                  {trust.total.toFixed(2)}
                </span>

                <button
                  type="button"
                  onClick={() => setShowTrustBreakdown((current) => !current)}
                  className="rounded-full text-xs text-zinc-600 transition hover:text-zinc-200"
                  aria-label="View trust score breakdown"
                >
                  ⓘ
                </button>
              </div>

              <p
                className={`mt-1 text-[10px] font-semibold tracking-wider ${authority.className}`}
              >
                {authority.label}
              </p>

              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-zinc-800">
                <div
                  className={`h-full rounded-full ${authority.barClassName}`}
                  style={{
                    width: `${Math.min(trust.total, 100)}%`,
                  }}
                />
              </div>

              {showTrustBreakdown && (
                <TrustBreakdown
                  scenario={scenario}
                  trust={trust}
                  onClose={() => setShowTrustBreakdown(false)}
                />
              )}
            </div>

            <Metric label="Requested" value={percentage(requestedDiscount)} />

            <Metric label="Rounds" value={String(result.rounds)} />

            <Metric
              label="Status"
              value={<StatusBadge status={result.status} />}
            />
          </div>

          {/* ---------------------------------------------------------------- */}
          {/* TRANSCRIPT + SIDEBAR                                             */}
          {/* ---------------------------------------------------------------- */}

          <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
            {/* TRANSCRIPT */}

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950">
              <div className="flex items-center justify-between border-b border-zinc-800 px-5 py-4">
                <div>
                  <p className="text-sm font-semibold text-white">
                    Negotiation Transcript
                  </p>

                  <p className="mt-1 break-all text-xs text-zinc-500">
                    {result.session_id}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={resetScenario}
                  className="rounded-lg border border-zinc-700 px-3 py-2 text-xs font-medium text-zinc-300 transition hover:border-zinc-500 hover:text-white"
                >
                  Adjust request
                </button>
              </div>

              <div className="max-h-[650px] space-y-3 overflow-y-auto p-5">
                {result.messages.map((message, index) => {
                  const buyer = isBuyerMessage(message);

                  return (
                    <div
                      key={`${message.round_number}-${index}`}
                      className={`flex ${
                        buyer ? "justify-start" : "justify-end"
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
                              buyer ? "text-zinc-500" : "text-blue-400"
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
                              message.proposed_price !== undefined) && (
                              <span className="rounded-lg bg-black/30 px-2.5 py-1.5 text-xs text-zinc-300">
                                {money(message.price ?? message.proposed_price)}
                              </span>
                            )}

                            {message.discount_pct !== undefined && (
                              <span className="rounded-lg bg-black/30 px-2.5 py-1.5 text-xs text-zinc-300">
                                {percentage(message.discount_pct)} discount
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

            {/* SIDEBAR */}

            <aside className="space-y-4">
              {/* FINAL DECISION */}

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

              {/* FINAL AUTHORIZATION GATE */}

              {scenario.id === "final-authorization" &&
                result.transaction_id && <FinalAuthorizationGate />}

              {/* TRANSACTION */}

              {result.transaction_id ? (
                <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-5">
                  <p className="text-xs uppercase tracking-[0.18em] text-zinc-600">
                    Transaction
                  </p>

                  <p className="mt-3 break-all font-mono text-xs text-emerald-300">
                    {result.transaction_id}
                  </p>

                  <div className="mt-5 grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-xs text-zinc-600">Final price</p>

                      <p className="mt-1 text-lg font-semibold text-white">
                        {money(result.final_price)}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs text-zinc-600">Discount</p>

                      <p className="mt-1 text-lg font-semibold text-white">
                        {percentage(result.final_discount_pct)}
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-5">
                  <p className="text-xs uppercase tracking-[0.18em] text-zinc-600">
                    Transaction
                  </p>

                  <p className="mt-3 text-sm text-zinc-500">
                    No transaction was authorized.
                  </p>
                </div>
              )}

              {/* RAZORPAY */}

              {result.transaction_id && result.status === "accepted" && (
                <RazorpayPaymentCard
                  result={result}
                  paymentState={paymentState}
                  paymentError={paymentError}
                  onPay={handlePayment}
                />
              )}

              {/* COMMERCE STATE */}

              <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-5">
                <p className="text-xs uppercase tracking-[0.18em] text-zinc-600">
                  Commerce State
                </p>

                <p className="mt-3 text-sm font-medium text-white">
                  {context.product.name}
                </p>

                <div className="mt-4 space-y-2 text-xs">
                  <Row
                    label="Listed price"
                    value={money(context.product.price)}
                  />

                  <Row
                    label="Inventory"
                    value={String(
                      scenario.inventory ?? context.product.inventory,
                    )}
                  />

                  <Row
                    label="Merchant ceiling"
                    value={percentage(context.merchant.max_discount_pct)}
                  />

                  <Row
                    label="Autonomy budget"
                    value={money(
                      scenario.allocatedBudget ?? context.merchant.daily_budget,
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

/* -------------------------------------------------------------------------- */
/* Final Authorization                                                        */
/* -------------------------------------------------------------------------- */

function FinalAuthorizationGate() {
  return (
    <div className="rounded-2xl border border-emerald-900/40 bg-emerald-950/10 p-5">
      <p className="text-xs uppercase tracking-[0.18em] text-emerald-500">
        Final Transaction Authorization
      </p>

      <p className="mt-3 text-sm font-semibold text-white">
        Accepted offer passed the authorization gate
      </p>

      <div className="mt-5 space-y-3">
        <GateRow label="Negotiation accepted" />

        <GateRow label="Trust policy" />

        <GateRow label="Merchant bounds" />

        <GateRow label="Autonomy budget" />

        <GateRow label="Cost protection" />
      </div>

      <div className="mt-5 border-t border-emerald-900/40 pt-4">
        <div className="flex items-center justify-between">
          <span className="text-xs text-zinc-500">Authorization result</span>

          <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[10px] font-semibold tracking-wider text-emerald-300">
            TRANSACTION AUTHORIZED
          </span>
        </div>
      </div>
    </div>
  );
}

function GateRow({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-zinc-400">{label}</span>

      <span className="font-semibold text-emerald-400">✓ PASS</span>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Razorpay Payment                                                           */
/* -------------------------------------------------------------------------- */

function RazorpayPaymentCard({
  result,
  paymentState,
  paymentError,
  onPay,
}: {
  result: NegotiationSessionResponse;
  paymentState:
    | "idle"
    | "creating"
    | "checkout"
    | "verifying"
    | "authorized"
    | "failed";
  paymentError: string | null;
  onPay: () => void;
}) {
  const paid = paymentState === "authorized";

  return (
    <div
      className={`rounded-2xl border p-5 ${
        paid
          ? "border-emerald-900/50 bg-emerald-950/10"
          : "border-orange-900/40 bg-orange-950/10"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">
            Razorpay Payment
          </p>

          <p className="mt-2 text-sm font-semibold text-white">
            {paid
              ? "Payment successfully authorized"
              : "Complete the authorized transaction"}
          </p>
        </div>

        {!paid && (
          <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-2.5 py-1 text-[10px] font-semibold tracking-wider text-orange-300">
            PAYMENT PENDING
          </span>
        )}
      </div>

      <div className="mt-5 rounded-xl border border-zinc-800 bg-black/20 p-4">
        <p className="text-xs text-zinc-600">Final amount</p>

        <p className="mt-1 text-2xl font-semibold text-white">
          {money(result.final_price)}
        </p>
      </div>

      {paid ? (
        <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3">
          <p className="text-sm font-semibold text-emerald-300">
            PAYMENT AUTHORIZED
          </p>

          <p className="mt-1 text-xs text-emerald-400/70">
            Razorpay payment was verified by Arbiter.
          </p>
        </div>
      ) : (
        <>
          <button
            type="button"
            onClick={onPay}
            disabled={
              paymentState === "creating" ||
              paymentState === "checkout" ||
              paymentState === "verifying"
            }
            className="mt-4 w-full rounded-xl bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {paymentState === "creating"
              ? "Creating Razorpay order..."
              : paymentState === "checkout"
                ? "Razorpay Checkout open..."
                : paymentState === "verifying"
                  ? "Verifying payment..."
                  : "Pay with Razorpay"}
          </button>

          {paymentError && (
            <div className="mt-3 rounded-lg border border-red-900/50 bg-red-950/20 p-3">
              <p className="text-xs text-red-300">{paymentError}</p>
            </div>
          )}

          {paymentState === "failed" && !paymentError && (
            <p className="mt-3 text-xs text-red-400">
              Payment could not be completed.
            </p>
          )}
        </>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Trust Breakdown                                                            */
/* -------------------------------------------------------------------------- */

function TrustBreakdown({
  scenario,
  trust,
  onClose,
}: {
  scenario: Scenario;
  trust: ReturnType<typeof calculateTrust>;
  onClose: () => void;
}) {
  return (
    <div className="absolute left-0 top-full z-50 mt-3 w-[340px] max-w-[calc(100vw-2rem)] rounded-2xl border border-zinc-700 bg-zinc-950 p-5 shadow-2xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-white">
            Trust Score Breakdown
          </p>

          <p className="mt-1 text-xs text-zinc-500">
            Deterministic weighted calculation
          </p>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="text-xs text-zinc-600 transition hover:text-white"
        >
          ✕
        </button>
      </div>

      <div className="mt-5 space-y-4">
        <TrustRow
          label="Identity confidence"
          value={scenario.buyerSignals.identity_confidence}
          weight="30%"
          contribution={trust.weighted.identity}
        />

        <TrustRow
          label="Intent confidence"
          value={scenario.buyerSignals.intent_confidence}
          weight="25%"
          contribution={trust.weighted.intent}
        />

        <TrustRow
          label="History score"
          value={scenario.buyerSignals.history_score}
          weight="20%"
          contribution={trust.weighted.history}
        />

        <TrustRow
          label="Violation score"
          value={trust.violationScore}
          weight="15%"
          contribution={trust.weighted.violations}
          suffix={`${scenario.buyerSignals.violation_count} violations`}
        />

        <TrustRow
          label="Behavior score"
          value={scenario.buyerSignals.behavior_score}
          weight="10%"
          contribution={trust.weighted.behavior}
        />
      </div>

      <div className="mt-5 border-t border-zinc-800 pt-4">
        <div className="flex items-center justify-between">
          <span className="text-xs text-zinc-500">Final calculated trust</span>

          <span className="font-semibold text-white">
            {trust.total.toFixed(2)} / 100
          </span>
        </div>

        <p className="mt-2 text-[10px] leading-4 text-zinc-600">
          Identity × 30% + Intent × 25% + History × 20% + Violations × 15% +
          Behavior × 10%
        </p>
      </div>
    </div>
  );
}

function TrustRow({
  label,
  value,
  weight,
  contribution,
  suffix,
}: {
  label: string;
  value: number;
  weight: string;
  contribution: number;
  suffix?: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-zinc-400">{label}</span>

        <span className="text-xs font-medium text-zinc-200">
          {value.toFixed(0)}
        </span>
      </div>

      <div className="mt-1 flex items-center justify-between">
        <span className="text-[10px] text-zinc-600">
          Weight {weight}
          {suffix ? ` · ${suffix}` : ""}
        </span>

        <span className="text-[10px] text-zinc-400">
          +{contribution.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Generic UI                                                                 */
/* -------------------------------------------------------------------------- */

function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-zinc-600">
        {label}
      </p>

      <div className="mt-2 text-lg font-semibold text-zinc-100">{value}</div>
    </div>
  );
}

function InfoBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-black/20 p-4">
      <p className="text-[10px] uppercase tracking-[0.14em] text-zinc-600">
        {label}
      </p>

      <p className="mt-2 text-sm font-semibold text-zinc-200">{value}</p>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-zinc-600">{label}</span>

      <span className="text-zinc-300">{value}</span>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

import {
  createPaymentOrder,
  getDemoContext,
  startNegotiation,
  type DemoContext,
  type NegotiationMessage,
  type NegotiationSessionResponse,
  type PaymentOrderResponse,
} from "@/lib/api";
function money(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

function trustScore(buyer: DemoContext["buyer"]) {
  return (
    buyer.identity_confidence * 0.3 +
    buyer.intent_confidence * 0.25 +
    buyer.history_score * 0.2 +
    (100 - Math.min(buyer.violation_count / 5, 1) * 100) * 0.15 +
    buyer.behavior_score * 0.1
  );
}

function messageRole(message: NegotiationMessage) {
  if (
    message.message_type === "purchase_request" ||
    message.message_type === "accept"
  ) {
    return "BUYER AGENT";
  }

  return "SELLER AGENT";
}

function messageIsBuyer(message: NegotiationMessage) {
  return messageRole(message) === "BUYER AGENT";
}

function cleanMessage(message: string) {
  return message.replace(/\*\*/g, "").replace(/\\n/g, "\n").trim();
}

export default function Home() {
  const [context, setContext] = useState<DemoContext | null>(null);
  const [discount, setDiscount] = useState(10);
  const [negotiation, setNegotiation] =
    useState<NegotiationSessionResponse | null>(null);
  const [paymentOrder, setPaymentOrder] = useState<PaymentOrderResponse | null>(
    null,
  );

  const [paymentLoading, setPaymentLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [negotiating, setNegotiating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDemoContext()
      .then(setContext)
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Unable to load Arbiter.",
        );
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleNegotiation() {
    if (!context) return;

    setNegotiating(true);
    setError(null);
    setNegotiation(null);

    try {
      const result = await startNegotiation(context, discount);
      setNegotiation(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Negotiation failed.");
    } finally {
      setNegotiating(false);
    }
  }
  async function handlePayment() {
    if (!negotiation?.transaction_id) {
      setError("No transaction is available for payment.");
      return;
    }

    setPaymentLoading(true);
    setError(null);

    try {
      const order = await createPaymentOrder(negotiation.transaction_id);

      setPaymentOrder(order);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to create payment order.",
      );
    } finally {
      setPaymentLoading(false);
    }
  }
  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0a0a0a] text-white">
        <p className="text-zinc-400">Loading Arbiter...</p>
      </main>
    );
  }

  if (error && !context) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0a0a0a] p-6 text-white">
        <div className="max-w-md rounded-2xl border border-red-900 bg-red-950/30 p-6">
          <h1 className="text-xl font-semibold">
            Unable to connect to Arbiter
          </h1>

          <p className="mt-2 text-sm text-red-300">{error}</p>
        </div>
      </main>
    );
  }

  if (!context) return null;

  const trust = trustScore(context.buyer);

  const authority =
    trust >= context.merchant.trust_full_threshold
      ? "FULL"
      : trust >= context.merchant.trust_restricted_threshold
        ? "RESTRICTED"
        : "BLOCK";

  const margin = context.product.price - context.product.cost;

  return (
    <main className="min-h-screen bg-[#0a0a0a] text-white">
      <div className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
        {/* Header */}
        <header className="flex items-center justify-between border-b border-zinc-800 pb-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white font-bold text-black">
              A
            </div>

            <div>
              <h1 className="text-xl font-semibold tracking-tight">ARBITER</h1>

              <p className="text-xs text-zinc-500">
                Trust-aware agentic commerce
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 rounded-full border border-emerald-900/50 bg-emerald-950/30 px-3 py-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />

            <span className="text-xs font-medium text-emerald-300">
              SYSTEM ONLINE
            </span>
          </div>
        </header>

        {/* Main grid */}
        <div className="mt-8 grid gap-6 lg:grid-cols-3">
          {/* Product */}
          <section className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6 lg:col-span-2">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">
                  Product
                </p>

                <h2 className="mt-2 text-3xl font-semibold">
                  {context.product.name}
                </h2>

                <p className="mt-2 max-w-xl text-sm text-zinc-400">
                  {context.product.description}
                </p>
              </div>

              <div className="rounded-xl border border-zinc-800 px-4 py-3 text-right">
                <p className="text-xs text-zinc-500">Inventory</p>

                <p className="mt-1 text-xl font-semibold">
                  {context.product.inventory}
                </p>
              </div>
            </div>

            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              <Metric label="List price" value={money(context.product.price)} />

              <Metric
                label="Merchant cost"
                value={money(context.product.cost)}
              />

              <Metric label="Protected margin" value={money(margin)} />
            </div>
          </section>

          {/* Buyer */}
          <section className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">
              Buyer
            </p>

            <div className="mt-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-800 font-semibold">
                D
              </div>

              <div>
                <h2 className="font-semibold">{context.buyer.buyer_id}</h2>

                <p className="text-xs text-emerald-400">Active buyer</p>
              </div>
            </div>

            <div className="mt-6">
              <div className="flex items-end justify-between">
                <span className="text-sm text-zinc-400">Trust score</span>

                <span className="text-3xl font-semibold">
                  {trust.toFixed(1)}
                </span>
              </div>

              <div className="mt-3 h-2 overflow-hidden rounded-full bg-zinc-800">
                <div
                  className="h-full rounded-full bg-white"
                  style={{
                    width: `${trust}%`,
                  }}
                />
              </div>

              <div className="mt-3 inline-flex rounded-full border border-zinc-700 px-3 py-1 text-xs font-medium">
                {authority} AUTHORITY
              </div>
            </div>
          </section>
        </div>

        {/* Trust / policy */}
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          {/* Trust signals */}
          <section className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">
              Trust signals
            </p>

            <div className="mt-5 space-y-4">
              <Signal
                label="Identity"
                value={context.buyer.identity_confidence}
              />

              <Signal label="Intent" value={context.buyer.intent_confidence} />

              <Signal label="History" value={context.buyer.history_score} />

              <Signal label="Behavior" value={context.buyer.behavior_score} />

              <Signal
                label="Violations"
                value={context.buyer.violation_count}
                suffix=" events"
                max={5}
              />
            </div>
          </section>

          {/* Merchant policy */}
          <section className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">
              Merchant policy
            </p>

            <div className="mt-5 grid grid-cols-2 gap-4">
              <Metric
                label="Max discount"
                value={`${context.merchant.max_discount_pct}%`}
              />

              <Metric
                label="Daily budget"
                value={money(context.merchant.daily_budget)}
              />

              <Metric
                label="Full authority"
                value={`≥ ${context.merchant.trust_full_threshold}`}
              />

              <Metric
                label="Restricted"
                value={`≥ ${context.merchant.trust_restricted_threshold}`}
              />
            </div>
          </section>
        </div>

        {/* Negotiation */}
        <section className="mt-6 rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="flex-1">
              <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">
                Negotiation
              </p>

              <h2 className="mt-2 text-2xl font-semibold">
                Buyer&apos;s requested discount
              </h2>

              <div className="mt-6 flex items-center gap-5">
                <input
                  type="range"
                  min="0"
                  max={context.merchant.max_discount_pct}
                  step="1"
                  value={discount}
                  onChange={(event) => setDiscount(Number(event.target.value))}
                  className="w-full accent-white"
                />

                <span className="w-16 text-right text-2xl font-semibold">
                  {discount}%
                </span>
              </div>

              <p className="mt-2 text-xs text-zinc-500">
                Merchant ceiling: {context.merchant.max_discount_pct}%
              </p>
            </div>

            <button
              onClick={handleNegotiation}
              disabled={negotiating}
              className="rounded-xl bg-white px-6 py-3 font-semibold text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {negotiating ? "NEGOTIATING..." : "START NEGOTIATION"}
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="mt-6 rounded-xl border border-red-900 bg-red-950/30 p-4 text-sm text-red-300">
              {error}
            </div>
          )}

          {/* Negotiation result */}
          {negotiation && (
            <div className="mt-8 border-t border-zinc-800 pt-6">
              {/* Accepted banner */}
              {negotiation.status === "accepted" && (
                <div className="mb-6 rounded-2xl border border-emerald-900/60 bg-emerald-950/20 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-400 font-semibold text-black">
                      ✓
                    </div>

                    <div>
                      <p className="text-xs font-medium uppercase tracking-[0.15em] text-emerald-400">
                        Deal accepted
                      </p>

                      <p className="mt-1 text-sm text-zinc-300">
                        Arbiter authorized the negotiated transaction.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Result metrics */}
              <div className="grid gap-4 sm:grid-cols-3">
                <Metric
                  label="Status"
                  value={negotiation.status.toUpperCase()}
                />

                <Metric
                  label="Final price"
                  value={
                    negotiation.final_price !== null
                      ? money(negotiation.final_price)
                      : "—"
                  }
                />

                <Metric
                  label="Final discount"
                  value={
                    negotiation.final_discount_pct !== null
                      ? `${negotiation.final_discount_pct}%`
                      : "—"
                  }
                />
              </div>

              {/* Agent response */}
              <div className="mt-6 rounded-xl border border-zinc-800 bg-black p-5">
                <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">
                  Agent response
                </p>

                <p className="mt-3 text-sm leading-6 text-zinc-300">
                  {cleanMessage(negotiation.message)}
                </p>
              </div>

              {/* Agent conversation */}
              {negotiation.messages.length > 0 && (
                <div className="mt-8 border-t border-zinc-800 pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">
                        Agent conversation
                      </p>

                      <h3 className="mt-1 text-lg font-semibold">
                        Negotiation transcript
                      </h3>
                    </div>

                    <div className="rounded-full border border-zinc-800 px-3 py-1 text-xs text-zinc-500">
                      {negotiation.rounds}{" "}
                      {negotiation.rounds === 1 ? "round" : "rounds"}
                    </div>
                  </div>

                  <div className="mt-6 space-y-5">
                    {negotiation.messages.map((message, index) => {
                      const buyer = messageIsBuyer(message);

                      return (
                        <div
                          key={index}
                          className={`flex ${
                            buyer ? "justify-start" : "justify-end"
                          }`}
                        >
                          <div
                            className={`flex max-w-2xl flex-col ${
                              buyer ? "items-start" : "items-end"
                            }`}
                          >
                            {/* Agent label */}
                            <div className="mb-2 flex items-center gap-2">
                              <span className="text-[10px] font-medium tracking-[0.15em] text-zinc-500">
                                {messageRole(message)}
                              </span>

                              <span className="text-[10px] text-zinc-700">
                                ROUND {message.round_number}
                              </span>
                            </div>

                            {/* Message bubble */}
                            <div
                              className={`rounded-2xl border px-5 py-4 ${
                                buyer
                                  ? "border-zinc-800 bg-zinc-900"
                                  : "border-white bg-white text-black"
                              }`}
                            >
                              <p className="whitespace-pre-line text-sm leading-6">
                                {cleanMessage(message.message)}
                              </p>

                              {/* Message metadata */}
                              {(message.price !== undefined ||
                                message.proposed_price !== undefined ||
                                message.discount_pct !== undefined) && (
                                <div
                                  className={`mt-4 flex flex-wrap gap-2 border-t pt-3 ${
                                    buyer
                                      ? "border-zinc-800"
                                      : "border-zinc-200"
                                  }`}
                                >
                                  {message.price !== undefined && (
                                    <span
                                      className={`rounded-full px-3 py-1 text-xs ${
                                        buyer
                                          ? "bg-zinc-800 text-zinc-300"
                                          : "bg-zinc-100 text-zinc-700"
                                      }`}
                                    >
                                      {money(message.price)}
                                    </span>
                                  )}

                                  {message.proposed_price !== undefined && (
                                    <span
                                      className={`rounded-full px-3 py-1 text-xs ${
                                        buyer
                                          ? "bg-zinc-800 text-zinc-300"
                                          : "bg-zinc-100 text-zinc-700"
                                      }`}
                                    >
                                      Proposed {money(message.proposed_price)}
                                    </span>
                                  )}

                                  {message.discount_pct !== undefined && (
                                    <span
                                      className={`rounded-full px-3 py-1 text-xs ${
                                        buyer
                                          ? "bg-zinc-800 text-zinc-300"
                                          : "bg-zinc-100 text-zinc-700"
                                      }`}
                                    >
                                      {message.discount_pct}% off
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Next action */}
              {negotiation.status === "accepted" && (
                <div className="mt-8 flex flex-col items-center border-t border-zinc-800 pt-8">
                  <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">
                    Next step
                  </p>

                  <h3 className="mt-2 text-xl font-semibold">
                    Ready to complete the transaction
                  </h3>

                  <p className="mt-2 text-center text-sm text-zinc-500">
                    The negotiated price has been authorized by Arbiter.
                  </p>

                  <button
                    type="button"
                    disabled={paymentLoading || !negotiation.transaction_id}
                    className="mt-5 rounded-xl bg-white px-8 py-3 text-sm font-semibold text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
                    onClick={handlePayment}
                  >
                    {paymentLoading
                      ? "CREATING PAYMENT..."
                      : "PROCEED TO PAYMENT"}
                  </button>
                  {paymentOrder && (
                    <div className="mt-6 w-full max-w-3xl rounded-xl border border-zinc-800 bg-black p-5">
                      <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">
                        Payment order created
                      </p>

                      <div className="mt-4 grid gap-4 sm:grid-cols-3">
                        <Metric
                          label="Order ID"
                          value={paymentOrder.razorpay_order_id}
                        />

                        <Metric
                          label="Amount"
                          value={money(paymentOrder.amount)}
                        />

                        <Metric
                          label="Status"
                          value={paymentOrder.status.toUpperCase()}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-black p-4">
      <p className="text-xs text-zinc-500">{label}</p>

      <p className="mt-2 text-lg font-semibold">{value}</p>
    </div>
  );
}

function Signal({
  label,
  value,
  suffix = "%",
  max = 100,
}: {
  label: string;
  value: number;
  suffix?: string;
  max?: number;
}) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <div>
      <div className="flex justify-between text-sm">
        <span className="text-zinc-400">{label}</span>

        <span className="font-medium">
          {value}
          {suffix}
        </span>
      </div>

      <div className="mt-2 h-1.5 rounded-full bg-zinc-800">
        <div
          className="h-full rounded-full bg-zinc-300"
          style={{
            width: `${percentage}%`,
          }}
        />
      </div>
    </div>
  );
}

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";

export type DemoContext = {
  merchant: {
    merchant_id: string;
    max_discount_pct: number;
    daily_budget: number;
    trust_full_threshold: number;
    trust_restricted_threshold: number;
  };
  buyer: {
    buyer_id: string;
    identity_confidence: number;
    intent_confidence: number;
    history_score: number;
    violation_count: number;
    behavior_score: number;
    is_active: boolean;
  };
  product: {
    id: number;
    merchant_id: string;
    name: string;
    description: string;
    price: number;
    cost: number;
    inventory: number;
  };
};
export type NegotiationMessage = {
  session_id?: string;
  buyer_id?: string;
  merchant_id?: string;
  product_id?: string;
  message_type: string;
  round_number: number;
  proposed_price?: number;
  requested_discount_pct?: number;
  discount_pct?: number;
  discount_value?: number;
  price?: number;
  message: string;
  requires_confirmation?: boolean;
};

export type NegotiationSessionResponse = {
  session_id: string;
  transaction_id: string | null;
  status: "active" | "accepted" | "rejected" | "blocked" | "expired";
  rounds: number;
  final_price: number | null;
  final_discount_pct: number | null;
  message: string;
  messages: NegotiationMessage[];
};
export type PaymentOrderResponse = {
  transaction_id: string;
  razorpay_order_id: string;
  amount: number;
  currency: string;
  status:
    | "payment_created"
    | "payment_pending";
};

export type PaymentVerifyResponse = {
  transaction_id: string;
  razorpay_payment_id: string;
  status: "payment_authorized";
  message: string;
};


export async function createPaymentOrder(
  transactionId: string,
): Promise<PaymentOrderResponse> {
  const response = await fetch(
    `${API_URL}/api/v1/payment/order`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        transaction_id: transactionId,
      }),
    },
  );

  if (!response.ok) {
    const error = await response.text();

    throw new Error(
      `Payment order failed: ${response.status} ${error}`,
    );
  }

  return response.json();
}


export async function verifyPayment(
  transactionId: string,
  razorpayOrderId: string,
  razorpayPaymentId: string,
  razorpaySignature: string,
): Promise<PaymentVerifyResponse> {
  const response = await fetch(
    `${API_URL}/api/v1/payment/verify`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        transaction_id: transactionId,
        razorpay_order_id: razorpayOrderId,
        razorpay_payment_id: razorpayPaymentId,
        razorpay_signature: razorpaySignature,
      }),
    },
  );

  if (!response.ok) {
    const error = await response.text();

    throw new Error(
      `Payment verification failed: ${response.status} ${error}`,
    );
  }

  return response.json();
}
export async function getDemoContext(): Promise<DemoContext> {
  const response = await fetch(
    `${API_URL}/api/v1/demo/context`,
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      `Failed to load demo context: ${response.status}`,
    );
  }

  return response.json();
}

export async function startNegotiation(
  context: DemoContext,
  requestedDiscountPct: number,
): Promise<NegotiationSessionResponse> {
  const response = await fetch(
    `${API_URL}/api/v1/negotiation/session`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        merchant_id: context.merchant.merchant_id,
        period: "demo",
        buyer_id: context.buyer.buyer_id,
        product_id: context.product.id,
        buyer_signals: {
          identity_confidence:
            context.buyer.identity_confidence,
          intent_confidence:
            context.buyer.intent_confidence,
          history_score:
            context.buyer.history_score,
          violation_count:
            context.buyer.violation_count,
          behavior_score:
            context.buyer.behavior_score,
        },
        requested_discount_pct: requestedDiscountPct,
        max_rounds: 5,
      }),
    },
  );

  if (!response.ok) {
    const error = await response.text();

    throw new Error(
      `Negotiation failed: ${response.status} ${error}`,
    );
  }

  return response.json();
}
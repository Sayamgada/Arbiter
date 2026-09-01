import os

import razorpay
from dotenv import load_dotenv


load_dotenv()


class PaymentService:
    """Thin adapter around the Razorpay API."""

    def __init__(self):
        key_id = os.getenv("RAZORPAY_KEY_ID")
        key_secret = os.getenv("RAZORPAY_KEY_SECRET")

        if not key_id or not key_secret:
            raise RuntimeError(
                "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET "
                "must be configured"
            )

        self.key_id = key_id
        self.client = razorpay.Client(
            auth=(key_id, key_secret)
        )

    def create_order(
        self,
        *,
        amount: float,
        currency: str = "INR",
        receipt: str,
    ) -> dict:
        """Create a Razorpay order and return its response."""

        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero")

        order = self.client.order.create(
            {
                "amount": int(round(amount * 100)),
                "currency": currency,
                "receipt": receipt,
            }
        )

        return order
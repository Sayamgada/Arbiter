from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.buyer import Buyer
from app.models.merchant import MerchantPolicy
from app.models.product import Product
from app.models.transaction import Transaction
from app.schemas.negotiation import TransactionStatus


client = TestClient(app)


def test_complete_intelligent_transaction_loop(db_session):
    merchant_id = "e2e_merchant"
    buyer_id = "e2e_buyer"

    buyer = Buyer(
        buyer_id=buyer_id,
        identity_confidence=100,
        intent_confidence=100,
        history_score=100,
        violation_count=0,
        behavior_score=100,
        is_active=True,
    )

    merchant_policy = MerchantPolicy(
        merchant_id=merchant_id,
        max_discount_pct=12,
        daily_budget=5000,
        trust_full_threshold=80,
        trust_restricted_threshold=40,
    )

    product = Product(
        merchant_id=merchant_id,
        name="E2E Demo Product",
        description="End-to-end transaction test product",
        price=10000,
        cost=7000,
        inventory=10,
    )

    db_session.add_all(
        [
            buyer,
            merchant_policy,
            product,
        ]
    )
    db_session.commit()
    db_session.refresh(buyer)
    db_session.refresh(product)

    app.dependency_overrides[get_db] = lambda: db_session

    try:
        # ---------------------------------------------------------
        # 1. ONE-SHOT NEGOTIATION EVALUATION
        # ---------------------------------------------------------
        #
        # The buyer requests 10%. The seller strategically counters.
        # This is only a hypothetical offer and must not enter
        # the payment lifecycle.
        #
        negotiation_response = client.post(
            "/api/v1/negotiation/decide",
            json={
                "merchant_id": merchant_id,
                "period": "e2e",
                "buyer_id": buyer_id,
                "product_id": product.id,
                "buyer_signals": {
                    "identity_confidence": 100,
                    "intent_confidence": 100,
                    "history_score": 100,
                    "violation_count": 0,
                    "behavior_score": 100,
                },
                "requested_discount_pct": 10,
            },
        )

        assert negotiation_response.status_code == 200

        negotiation = negotiation_response.json()

        assert negotiation["decision"] == "counter"
        assert 0 < negotiation["discount_pct"] < 10
        assert negotiation["discount_pct"] <= 12
        assert negotiation["final_price"] < 10000
        assert negotiation["final_price"] >= 7000

        counter_transaction_id = negotiation["transaction_id"]

        counter_transaction = (
            db_session.query(Transaction)
            .filter(
                Transaction.transaction_id
                == counter_transaction_id
            )
            .first()
        )

        assert counter_transaction is not None
        assert (
            counter_transaction.status
            == TransactionStatus.CANCELLED.value
        )

        # The counter is hypothetical; no payment can be created
        # from this transaction.

        # ---------------------------------------------------------
        # 2. MULTI-ROUND NEGOTIATION -> ACCEPTED
        # ---------------------------------------------------------
        session_response = client.post(
            "/api/v1/negotiation/session",
            json={
                "merchant_id": merchant_id,
                "period": "e2e",
                "buyer_id": buyer_id,
                "product_id": product.id,
                "buyer_signals": {
                    "identity_confidence": 100,
                    "intent_confidence": 100,
                    "history_score": 100,
                    "violation_count": 0,
                    "behavior_score": 100,
                },
                "requested_discount_pct": 10,
                "max_rounds": 5,
            },
        )

        assert session_response.status_code == 200

        session = session_response.json()

        assert session["status"] == "accepted"
        assert session["transaction_id"] is not None
        assert session["rounds"] > 1
        assert session["rounds"] <= 5

        assert session["final_discount_pct"] is not None
        assert 0 < session["final_discount_pct"] < 10
        assert session["final_discount_pct"] >= 7

        assert session["final_price"] is not None
        assert session["final_price"] < 10000
        assert session["final_price"] >= 7000

        assert len(session["messages"]) >= session["rounds"]

        transaction_id = session["transaction_id"]

        transaction = (
            db_session.query(Transaction)
            .filter(
                Transaction.transaction_id == transaction_id
            )
            .first()
        )

        assert transaction is not None
        assert transaction.buyer_id == buyer.id
        assert transaction.product_id == product.id
        assert transaction.merchant_id == merchant_id

        assert transaction.decision == "approve"
        assert (
            transaction.status
            == TransactionStatus.PAYMENT_PENDING.value
        )

        # The final persisted offer must match the accepted
        # negotiation result.
        assert (
            transaction.final_offer["discount_pct"]
            == session["final_discount_pct"]
        )
        assert (
            transaction.final_offer["final_price"]
            == session["final_price"]
        )

        # ---------------------------------------------------------
        # 3. AUDIT TRAIL
        # ---------------------------------------------------------
        audit = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.transaction_id == transaction.id
            )
            .first()
        )

        assert audit is not None
        assert audit.decision == "approve"
        assert audit.trust_snapshot["score"] == 100
        assert audit.trust_snapshot["authority"] == "full"

        assert (
            audit.offer_snapshot["discount_pct"]
            == session["final_discount_pct"]
        )
        assert (
            audit.offer_snapshot["final_price"]
            == session["final_price"]
        )

        # ---------------------------------------------------------
        # 4. PAYMENT_PENDING -> PAYMENT_CREATED
        # ---------------------------------------------------------
        final_price = session["final_price"]

        with patch(
            "app.api.negotiation.PaymentService.create_order",
            return_value={
                "id": "order_e2e_123",
                "amount": int(final_price * 100),
                "currency": "INR",
            },
        ):
            order_response = client.post(
                "/api/v1/payment/order",
                json={
                    "transaction_id": transaction_id,
                },
            )

        assert order_response.status_code == 200

        order = order_response.json()

        assert order["transaction_id"] == transaction_id
        assert order["razorpay_order_id"] == "order_e2e_123"
        assert order["amount"] == final_price
        assert order["currency"] == "INR"
        assert (
            order["status"]
            == TransactionStatus.PAYMENT_CREATED.value
        )

        transaction = (
            db_session.query(Transaction)
            .filter(
                Transaction.transaction_id == transaction_id
            )
            .first()
        )

        assert (
            transaction.status
            == TransactionStatus.PAYMENT_CREATED.value
        )
        assert transaction.razorpay_ref == "order_e2e_123"

        # ---------------------------------------------------------
        # 5. PAYMENT_CREATED -> PAYMENT_AUTHORIZED
        # ---------------------------------------------------------
        with patch(
            "app.api.negotiation.PaymentService.verify_payment",
            return_value=True,
        ):
            verify_response = client.post(
                "/api/v1/payment/verify",
                json={
                    "transaction_id": transaction_id,
                    "razorpay_order_id": "order_e2e_123",
                    "razorpay_payment_id": "pay_e2e_123",
                    "razorpay_signature": "signature_e2e",
                },
            )

        assert verify_response.status_code == 200

        verification = verify_response.json()

        assert verification["transaction_id"] == transaction_id
        assert (
            verification["razorpay_payment_id"]
            == "pay_e2e_123"
        )
        assert (
            verification["status"]
            == TransactionStatus.PAYMENT_AUTHORIZED.value
        )

        # ---------------------------------------------------------
        # 6. FINAL DATABASE STATE
        # ---------------------------------------------------------
        transaction = (
            db_session.query(Transaction)
            .filter(
                Transaction.transaction_id == transaction_id
            )
            .first()
        )

        assert transaction is not None
        assert (
            transaction.status
            == TransactionStatus.PAYMENT_AUTHORIZED.value
        )
        assert transaction.razorpay_ref == "pay_e2e_123"

        assert (
            transaction.final_offer["discount_pct"]
            == session["final_discount_pct"]
        )
        assert (
            transaction.final_offer["discount_value"]
            == round(
                10000
                * session["final_discount_pct"]
                / 100,
                2,
            )
        )
        assert (
            transaction.final_offer["final_price"]
            == session["final_price"]
        )

    finally:
        app.dependency_overrides.clear()

        db_session.query(AuditLog).delete()
        db_session.query(Transaction).delete()
        db_session.query(Product).delete()
        db_session.query(MerchantPolicy).delete()
        db_session.query(Buyer).delete()

        db_session.commit()
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
from app.services.transaction_service import TransactionService


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
        # 1. NEGOTIATION -> NDC -> TRANSACTION
        # ---------------------------------------------------------
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

        assert negotiation["decision"] == "approve"
        assert negotiation["discount_pct"] == 10
        assert negotiation["discount_value"] == 1000
        assert negotiation["final_price"] == 9000

        transaction_id = negotiation["transaction_id"]

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
            == TransactionStatus.PAYMENT_PENDING.value
        )

        # ---------------------------------------------------------
        # 2. PAYMENT_PENDING -> PAYMENT_CREATED
        # ---------------------------------------------------------
        assert (
            transaction.status
            == TransactionStatus.PAYMENT_PENDING.value
        )

        # ---------------------------------------------------------
        # 3. AUDIT TRAIL EXISTS
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
        assert audit.offer_snapshot["discount_pct"] == 10
        assert audit.offer_snapshot["final_price"] == 9000

        # ---------------------------------------------------------
        # 4. PAYMENT_PENDING -> PAYMENT_CREATED
        # ---------------------------------------------------------
        with patch(
            "app.api.negotiation.PaymentService.create_order",
            return_value={
                "id": "order_e2e_123",
                "amount": 900000,
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
        assert order["amount"] == 9000
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
        assert verification["razorpay_payment_id"] == "pay_e2e_123"
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

        assert transaction.final_offer["discount_pct"] == 10
        assert transaction.final_offer["discount_value"] == 1000
        assert transaction.final_offer["final_price"] == 9000

    finally:
        app.dependency_overrides.clear()

        db_session.query(AuditLog).delete()
        db_session.query(Transaction).delete()
        db_session.query(Product).delete()
        db_session.query(MerchantPolicy).delete()
        db_session.query(Buyer).delete()

        db_session.commit()
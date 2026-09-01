from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.negotiation import TransactionStatus


client = TestClient(app)


def test_payment_verify_transaction_not_found():
    with patch(
        "app.api.negotiation.TransactionService.get_by_transaction_id",
        return_value=None,
    ):
        response = client.post(
            "/api/v1/payment/verify",
            json={
                "transaction_id": "txn_missing",
                "razorpay_order_id": "order_123",
                "razorpay_payment_id": "pay_123",
                "razorpay_signature": "signature",
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"


def test_payment_verify_requires_payment_created():
    transaction = MagicMock()
    transaction.status = TransactionStatus.PAYMENT_PENDING.value

    with patch(
        "app.api.negotiation.TransactionService.get_by_transaction_id",
        return_value=transaction,
    ):
        response = client.post(
            "/api/v1/payment/verify",
            json={
                "transaction_id": "txn_pending",
                "razorpay_order_id": "order_123",
                "razorpay_payment_id": "pay_123",
                "razorpay_signature": "signature",
            },
        )

    assert response.status_code == 400
    assert "payment_created" in response.json()["detail"]


def test_payment_verify_rejects_wrong_order():
    transaction = MagicMock()
    transaction.status = TransactionStatus.PAYMENT_CREATED.value
    transaction.razorpay_ref = "order_expected"

    with patch(
        "app.api.negotiation.TransactionService.get_by_transaction_id",
        return_value=transaction,
    ):
        response = client.post(
            "/api/v1/payment/verify",
            json={
                "transaction_id": "txn_test",
                "razorpay_order_id": "order_wrong",
                "razorpay_payment_id": "pay_123",
                "razorpay_signature": "signature",
            },
        )

    assert response.status_code == 400
    assert "does not match" in response.json()["detail"]


def test_payment_verify_success():
    transaction = MagicMock()
    transaction.transaction_id = "txn_test"
    transaction.status = TransactionStatus.PAYMENT_CREATED.value
    transaction.razorpay_ref = "order_123"

    with patch(
        "app.api.negotiation.TransactionService.get_by_transaction_id",
        return_value=transaction,
    ), patch(
        "app.api.negotiation.PaymentService.verify_payment",
        return_value=True,
    ) as verify_payment, patch(
        "app.api.negotiation.TransactionService.update_status",
        return_value=transaction,
    ) as update_status:

        response = client.post(
            "/api/v1/payment/verify",
            json={
                "transaction_id": "txn_test",
                "razorpay_order_id": "order_123",
                "razorpay_payment_id": "pay_123",
                "razorpay_signature": "signature",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["transaction_id"] == "txn_test"
    assert data["razorpay_payment_id"] == "pay_123"
    assert data["status"] == TransactionStatus.PAYMENT_AUTHORIZED.value
    assert data["message"] == "Payment verified successfully."

    verify_payment.assert_called_once_with(
        order_id="order_123",
        payment_id="pay_123",
        signature="signature",
    )

    update_status.assert_called_once_with(
        transaction=transaction,
        status=TransactionStatus.PAYMENT_AUTHORIZED,
        razorpay_ref="pay_123",
    )

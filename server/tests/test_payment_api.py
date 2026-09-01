from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.negotiation import TransactionStatus


client = TestClient(app)


def test_payment_order_transaction_not_found():
    with patch(
        "app.api.negotiation.TransactionService.get_by_transaction_id",
        return_value=None,
    ):
        response = client.post(
            "/api/v1/payment/order",
            json={
                "transaction_id": "txn_missing",
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"


def test_payment_order_requires_payment_pending():
    transaction = MagicMock()
    transaction.status = TransactionStatus.COMPLETED.value

    with patch(
        "app.api.negotiation.TransactionService.get_by_transaction_id",
        return_value=transaction,
    ):
        response = client.post(
            "/api/v1/payment/order",
            json={
                "transaction_id": "txn_completed",
            },
        )

    assert response.status_code == 400
    assert "payment_pending" in response.json()["detail"]


def test_payment_order_requires_valid_final_price():
    transaction = MagicMock()
    transaction.status = TransactionStatus.PAYMENT_PENDING.value
    transaction.final_offer = {}

    with patch(
        "app.api.negotiation.TransactionService.get_by_transaction_id",
        return_value=transaction,
    ):
        response = client.post(
            "/api/v1/payment/order",
            json={
                "transaction_id": "txn_invalid",
            },
        )

    assert response.status_code == 400
    assert "valid final price" in response.json()["detail"]


def test_payment_order_handles_razorpay_failure():
    transaction = MagicMock()
    transaction.status = TransactionStatus.PAYMENT_PENDING.value
    transaction.final_offer = {
        "final_price": 1499.50,
    }

    with patch(
        "app.api.negotiation.TransactionService.get_by_transaction_id",
        return_value=transaction,
    ), patch(
        "app.api.negotiation.PaymentService.create_order",
        side_effect=Exception("Razorpay unavailable"),
    ):
        response = client.post(
            "/api/v1/payment/order",
            json={
                "transaction_id": "txn_payment_error",
            },
        )

    assert response.status_code == 502
    assert "Unable to create payment order" in response.json()["detail"]


def test_payment_order_success():
    transaction = MagicMock()
    transaction.transaction_id = "txn_test_123"
    transaction.status = TransactionStatus.PAYMENT_PENDING.value
    transaction.final_offer = {
        "final_price": 1499.50,
    }

    updated_transaction = MagicMock()
    updated_transaction.transaction_id = "txn_test_123"

    with patch(
        "app.api.negotiation.TransactionService.get_by_transaction_id",
        return_value=transaction,
    ), patch(
        "app.api.negotiation.PaymentService.create_order",
        return_value={
            "id": "order_test_123",
            "amount": 149950,
            "currency": "INR",
        },
    ) as create_order, patch(
        "app.api.negotiation.TransactionService.update_status",
        return_value=updated_transaction,
    ) as update_status:

        response = client.post(
            "/api/v1/payment/order",
            json={
                "transaction_id": "txn_test_123",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["transaction_id"] == "txn_test_123"
    assert data["razorpay_order_id"] == "order_test_123"
    assert data["amount"] == 1499.50
    assert data["currency"] == "INR"
    assert data["status"] == TransactionStatus.PAYMENT_CREATED.value

    create_order.assert_called_once_with(
        amount=1499.50,
        currency="INR",
        receipt="txn_test_123",
    )

    update_status.assert_called_once_with(
        transaction=transaction,
        status=TransactionStatus.PAYMENT_CREATED,
        razorpay_ref="order_test_123",
    )


def test_payment_verify_transaction_not_found():
    with patch(
        "app.api.negotiation.TransactionService.get_by_transaction_id",
        return_value=None,
    ):
        response = client.post(
            "/api/v1/payment/verify",
            json={
                "transaction_id": "txn_missing",
                "razorpay_order_id": "order_test_123",
                "razorpay_payment_id": "pay_test_123",
                "razorpay_signature": "signature_test",
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
                "razorpay_order_id": "order_test_123",
                "razorpay_payment_id": "pay_test_123",
                "razorpay_signature": "signature_test",
            },
        )

    assert response.status_code == 400
    assert "payment_created" in response.json()["detail"]


def test_payment_verify_rejects_mismatched_order():
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
                "transaction_id": "txn_test_123",
                "razorpay_order_id": "order_wrong",
                "razorpay_payment_id": "pay_test_123",
                "razorpay_signature": "signature_test",
            },
        )

    assert response.status_code == 400
    assert "does not match transaction" in response.json()["detail"]


def test_payment_verify_handles_invalid_signature():
    transaction = MagicMock()
    transaction.transaction_id = "txn_test_123"
    transaction.status = TransactionStatus.PAYMENT_CREATED.value
    transaction.razorpay_ref = "order_test_123"

    with patch(
        "app.api.negotiation.TransactionService.get_by_transaction_id",
        return_value=transaction,
    ), patch(
        "app.api.negotiation.PaymentService.verify_payment",
        side_effect=Exception("Invalid signature"),
    ), patch(
        "app.api.negotiation.TransactionService.update_status",
    ) as update_status:

        response = client.post(
            "/api/v1/payment/verify",
            json={
                "transaction_id": "txn_test_123",
                "razorpay_order_id": "order_test_123",
                "razorpay_payment_id": "pay_test_123",
                "razorpay_signature": "bad_signature",
            },
        )

    assert response.status_code == 400
    assert "Payment verification failed" in response.json()["detail"]

    update_status.assert_called_once_with(
        transaction=transaction,
        status=TransactionStatus.PAYMENT_FAILED,
    )


def test_payment_verify_success():
    transaction = MagicMock()
    transaction.transaction_id = "txn_test_123"
    transaction.status = TransactionStatus.PAYMENT_CREATED.value
    transaction.razorpay_ref = "order_test_123"

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
                "transaction_id": "txn_test_123",
                "razorpay_order_id": "order_test_123",
                "razorpay_payment_id": "pay_test_123",
                "razorpay_signature": "valid_signature",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["transaction_id"] == "txn_test_123"
    assert data["razorpay_payment_id"] == "pay_test_123"
    assert data["status"] == TransactionStatus.PAYMENT_AUTHORIZED.value
    assert data["message"] == "Payment verified successfully."

    verify_payment.assert_called_once_with(
        order_id="order_test_123",
        payment_id="pay_test_123",
        signature="valid_signature",
    )

    update_status.assert_called_once_with(
        transaction=transaction,
        status=TransactionStatus.PAYMENT_AUTHORIZED,
        razorpay_ref="pay_test_123",
    )

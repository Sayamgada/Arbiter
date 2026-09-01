from unittest.mock import MagicMock, patch

import pytest

from app.services.payment_service import PaymentService


def test_payment_service_requires_credentials():
    with patch.dict(
        "os.environ",
        {},
        clear=True,
    ):
        with pytest.raises(RuntimeError):
            PaymentService()


def test_create_order_converts_amount_to_paise():
    with patch.dict(
        "os.environ",
        {
            "RAZORPAY_KEY_ID": "rzp_test_fake",
            "RAZORPAY_KEY_SECRET": "fake_secret",
        },
        clear=False,
    ):
        with patch("app.services.payment_service.razorpay.Client") as client:
            mock_client = MagicMock()
            client.return_value = mock_client

            mock_client.order.create.return_value = {
                "id": "order_test_123",
                "amount": 149950,
                "currency": "INR",
            }

            service = PaymentService()

            result = service.create_order(
                amount=1499.50,
                receipt="txn_test_123",
            )

            mock_client.order.create.assert_called_once_with(
                {
                    "amount": 149950,
                    "currency": "INR",
                    "receipt": "txn_test_123",
                }
            )

            assert result["id"] == "order_test_123"


def test_create_order_rejects_non_positive_amount():
    with patch.dict(
        "os.environ",
        {
            "RAZORPAY_KEY_ID": "rzp_test_fake",
            "RAZORPAY_KEY_SECRET": "fake_secret",
        },
        clear=False,
    ):
        with patch("app.services.payment_service.razorpay.Client"):
            service = PaymentService()

            with pytest.raises(ValueError):
                service.create_order(
                    amount=0,
                    receipt="txn_test_123",
                )
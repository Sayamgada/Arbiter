from types import SimpleNamespace

import pytest

from app.models.audit import AuditLog
from app.models.transaction import Transaction
from app.schemas.negotiation import (
    AuthorityTier,
    DecisionType,
    TransactionStatus,
)
from app.services.transaction_service import TransactionService


def make_result(
    *,
    decision=DecisionType.APPROVE,
    trust_score=95.0,
    discount_pct=10.0,
    discount_value=100.0,
    final_price=900.0,
    budget_remaining=900.0,
    reason="Approved within policy bounds.",
):
    return SimpleNamespace(
        decision=decision,
        authority=AuthorityTier.FULL,
        trust_score=trust_score,
        discount_pct=discount_pct,
        discount_value=discount_value,
        final_price=final_price,
        budget_remaining=budget_remaining,
        reason=reason,
    )


def test_create_from_decision_approved(db_session):
    service = TransactionService(db_session)

    result = make_result(
        decision=DecisionType.APPROVE,
    )

    transaction = service.create_from_decision(
        buyer_id=1,
        merchant_id="test-merchant",
        product_id=1,
        proposed_offer={
            "requested_discount_pct": 10,
            "product_price": 1000,
            "product_cost": 700,
        },
        result=result,
    )

    assert transaction.transaction_id.startswith("txn_")
    assert transaction.decision == "approve"
    assert transaction.status == TransactionStatus.PAYMENT_PENDING.value
    assert transaction.final_offer["discount_pct"] == 10.0
    assert transaction.final_offer["discount_value"] == 100.0
    assert transaction.final_offer["final_price"] == 900.0

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.transaction_id == transaction.id)
        .first()
    )

    assert audit is not None
    assert audit.decision == "approve"
    assert audit.trust_snapshot["score"] == 95.0
    assert audit.offer_snapshot["final_price"] == 900.0


def test_create_from_decision_non_approved_is_cancelled(db_session):
    service = TransactionService(db_session)

    result = make_result(
        decision=DecisionType.BLOCK,
        reason="Buyer blocked by policy.",
    )

    transaction = service.create_from_decision(
        buyer_id=1,
        merchant_id="test-merchant",
        product_id=1,
        proposed_offer={
            "requested_discount_pct": 50,
            "product_price": 1000,
            "product_cost": 700,
        },
        result=result,
    )

    assert transaction.decision == "block"
    assert transaction.status == TransactionStatus.CANCELLED.value


def test_valid_status_transition(db_session):
    transaction = Transaction(
        transaction_id="txn_transition_test",
        buyer_id=1,
        merchant_id="test-merchant",
        product_id=1,
        proposed_offer={},
        final_offer={},
        decision="approve",
        status=TransactionStatus.PAYMENT_PENDING.value,
        razorpay_ref="",
    )

    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)

    service = TransactionService(db_session)

    updated = service.update_status(
        transaction=transaction,
        status=TransactionStatus.PAYMENT_CREATED,
        razorpay_ref="order_test_123",
    )

    assert updated.status == TransactionStatus.PAYMENT_CREATED.value
    assert updated.razorpay_ref == "order_test_123"


def test_invalid_status_transition_raises(db_session):
    transaction = Transaction(
        transaction_id="txn_invalid_transition_test",
        buyer_id=1,
        merchant_id="test-merchant",
        product_id=1,
        proposed_offer={},
        final_offer={},
        decision="approve",
        status=TransactionStatus.PAYMENT_PENDING.value,
        razorpay_ref="",
    )

    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)

    service = TransactionService(db_session)

    with pytest.raises(ValueError, match="Invalid transaction status transition"):
        service.update_status(
            transaction=transaction,
            status=TransactionStatus.COMPLETED,
        )


def test_get_by_transaction_id(db_session):
    transaction = Transaction(
        transaction_id="txn_lookup_test",
        buyer_id=1,
        merchant_id="test-merchant",
        product_id=1,
        proposed_offer={},
        final_offer={},
        decision="approve",
        status=TransactionStatus.PAYMENT_PENDING.value,
        razorpay_ref="",
    )

    db_session.add(transaction)
    db_session.commit()

    service = TransactionService(db_session)

    found = service.get_by_transaction_id("txn_lookup_test")

    assert found is not None
    assert found.id == transaction.id


def test_get_by_transaction_id_missing(db_session):
    service = TransactionService(db_session)

    found = service.get_by_transaction_id("txn_does_not_exist")

    assert found is None
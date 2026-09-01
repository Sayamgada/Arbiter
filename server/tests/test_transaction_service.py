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


def test_create_from_decision_approved(
    db_session,
    transaction_dependencies,
):
    buyer, product = transaction_dependencies
    service = TransactionService(db_session)

    result = make_result(
        decision=DecisionType.APPROVE,
    )

    transaction = service.create_from_decision(
        buyer_id=buyer.id,
        merchant_id="test-merchant",
        product_id=product.id,
        proposed_offer={
            "requested_discount_pct": 10,
            "product_price": 1000,
            "product_cost": 700,
        },
        result=result,
    )

    assert transaction.transaction_id.startswith("txn_")
    assert transaction.decision == "approve"
    assert transaction.status == TransactionStatus.ACCEPTED.value

    assert transaction.final_offer["discount_pct"] == 10.0
    assert transaction.final_offer["discount_value"] == 100.0
    assert transaction.final_offer["final_price"] == 900.0

    audit = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.transaction_id == transaction.id
        )
        .first()
    )

    assert audit is not None
    assert audit.decision == "approve"
    assert audit.trust_snapshot["score"] == 95.0
    assert audit.offer_snapshot["final_price"] == 900.0


def test_create_from_decision_non_approved_is_cancelled(
    db_session,
    transaction_dependencies,
):
    buyer, product = transaction_dependencies
    service = TransactionService(db_session)

    result = make_result(
        decision=DecisionType.BLOCK,
        reason="Buyer blocked by policy.",
    )

    transaction = service.create_from_decision(
        buyer_id=buyer.id,
        merchant_id="test-merchant",
        product_id=product.id,
        proposed_offer={
            "requested_discount_pct": 50,
            "product_price": 1000,
            "product_cost": 700,
        },
        result=result,
    )

    assert transaction.decision == "block"
    assert transaction.status == TransactionStatus.CANCELLED.value


def test_valid_status_transition(
    db_session,
    transaction_dependencies,
):
    buyer, product = transaction_dependencies

    transaction = Transaction(
        transaction_id="txn_transition_test",
        buyer_id=buyer.id,
        merchant_id="test-merchant",
        product_id=product.id,
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


def test_invalid_status_transition_raises(
    db_session,
    transaction_dependencies,
):
    buyer, product = transaction_dependencies

    transaction = Transaction(
        transaction_id="txn_invalid_transition_test",
        buyer_id=buyer.id,
        merchant_id="test-merchant",
        product_id=product.id,
        proposed_offer={},
        final_offer={},
        decision="approve",
        status=TransactionStatus.PAYMENT_PENDING.value,
        razorpay_ref="",
    )

    db_session.add(transaction)
    db_session.commit()

    service = TransactionService(db_session)

    with pytest.raises(
        ValueError,
        match="Invalid transaction status transition",
    ):
        service.update_status(
            transaction=transaction,
            status=TransactionStatus.ACCEPTED,
        )


def test_get_by_transaction_id(
    db_session,
    transaction_dependencies,
):
    buyer, product = transaction_dependencies

    transaction = Transaction(
        transaction_id="txn_lookup_test",
        buyer_id=buyer.id,
        merchant_id="test-merchant",
        product_id=product.id,
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

    found = service.get_by_transaction_id(
        "txn_lookup_test"
    )

    assert found is not None
    assert found.id == transaction.id


def test_get_by_transaction_id_missing(db_session):
    service = TransactionService(db_session)

    found = service.get_by_transaction_id(
        "txn_does_not_exist"
    )

    assert found is None


def test_status_transition_creates_audit_log(
    db_session,
    transaction_dependencies,
):
    buyer, product = transaction_dependencies

    transaction = Transaction(
        transaction_id="txn_audit_transition_test",
        buyer_id=buyer.id,
        merchant_id="test-merchant",
        product_id=product.id,
        proposed_offer={},
        final_offer={
            "discount_pct": 10.0,
            "discount_value": 100.0,
            "final_price": 900.0,
        },
        decision="approve",
        status=TransactionStatus.PAYMENT_PENDING.value,
        razorpay_ref="",
    )

    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)

    service = TransactionService(db_session)

    service.update_status(
        transaction=transaction,
        status=TransactionStatus.PAYMENT_CREATED,
        razorpay_ref="order_test_123",
    )

    audits = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.transaction_id == transaction.id
        )
        .all()
    )

    assert len(audits) == 1

    audit = audits[0]

    assert audit.bounds_snapshot["previous_status"] == (
        TransactionStatus.PAYMENT_PENDING.value
    )
    assert audit.bounds_snapshot["new_status"] == (
        TransactionStatus.PAYMENT_CREATED.value
    )

    assert audit.offer_snapshot["final_price"] == 900.0

    assert "payment_pending" in audit.reasoning_text
    assert "payment_created" in audit.reasoning_text


def test_invalid_transition_does_not_create_audit_log(
    db_session,
    transaction_dependencies,
):
    buyer, product = transaction_dependencies

    transaction = Transaction(
        transaction_id="txn_invalid_audit_test",
        buyer_id=buyer.id,
        merchant_id="test-merchant",
        product_id=product.id,
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

    with pytest.raises(
        ValueError,
        match="Invalid transaction status transition",
    ):
        service.update_status(
            transaction=transaction,
            status=TransactionStatus.COMPLETED,
        )

    audits = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.transaction_id == transaction.id
        )
        .all()
    )

    assert audits == []


def test_mark_completed_from_payment_authorized(
    db_session,
    transaction_dependencies,
):
    buyer, product = transaction_dependencies

    transaction = Transaction(
        transaction_id="txn_complete_test",
        buyer_id=buyer.id,
        merchant_id="test-merchant",
        product_id=product.id,
        proposed_offer={},
        final_offer={
            "discount_pct": 10.0,
            "discount_value": 100.0,
            "final_price": 900.0,
        },
        decision="approve",
        status=TransactionStatus.PAYMENT_AUTHORIZED.value,
        razorpay_ref="pay_test_123",
    )

    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)

    service = TransactionService(db_session)

    completed = service.mark_completed(
        transaction=transaction,
    )

    assert completed.status == TransactionStatus.COMPLETED.value


def test_mark_completed_creates_audit_log(
    db_session,
    transaction_dependencies,
):
    buyer, product = transaction_dependencies

    transaction = Transaction(
        transaction_id="txn_complete_audit_test",
        buyer_id=buyer.id,
        merchant_id="test-merchant",
        product_id=product.id,
        proposed_offer={},
        final_offer={
            "discount_pct": 10.0,
            "discount_value": 100.0,
            "final_price": 900.0,
        },
        decision="approve",
        status=TransactionStatus.PAYMENT_AUTHORIZED.value,
        razorpay_ref="pay_test_123",
    )

    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)

    service = TransactionService(db_session)

    service.mark_completed(
        transaction=transaction,
    )

    audit = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.transaction_id == transaction.id
        )
        .first()
    )

    assert audit is not None

    assert (
        audit.bounds_snapshot["previous_status"]
        == TransactionStatus.PAYMENT_AUTHORIZED.value
    )
    assert (
        audit.bounds_snapshot["new_status"]
        == TransactionStatus.COMPLETED.value
    )

    assert audit.offer_snapshot["final_price"] == 900.0
    assert audit.offer_snapshot["discount_pct"] == 10.0
    assert audit.offer_snapshot["discount_value"] == 100.0

    assert "payment_authorized" in audit.reasoning_text
    assert "completed" in audit.reasoning_text


def test_completed_transaction_cannot_be_completed_again(
    db_session,
    transaction_dependencies,
):
    buyer, product = transaction_dependencies

    transaction = Transaction(
        transaction_id="txn_double_complete_test",
        buyer_id=buyer.id,
        merchant_id="test-merchant",
        product_id=product.id,
        proposed_offer={},
        final_offer={},
        decision="approve",
        status=TransactionStatus.COMPLETED.value,
        razorpay_ref="pay_test_123",
    )

    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)

    service = TransactionService(db_session)

    with pytest.raises(
        ValueError,
        match="Invalid transaction status transition",
    ):
        service.mark_completed(
            transaction=transaction,
        )


def test_completed_transaction_cannot_be_cancelled(
    db_session,
    transaction_dependencies,
):
    buyer, product = transaction_dependencies

    transaction = Transaction(
        transaction_id="txn_completed_cancel_test",
        buyer_id=buyer.id,
        merchant_id="test-merchant",
        product_id=product.id,
        proposed_offer={},
        final_offer={},
        decision="approve",
        status=TransactionStatus.COMPLETED.value,
        razorpay_ref="pay_test_123",
    )

    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)

    service = TransactionService(db_session)

    with pytest.raises(
        ValueError,
        match="Invalid transaction status transition",
    ):
        service.update_status(
            transaction=transaction,
            status=TransactionStatus.CANCELLED,
        )

    audits = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.transaction_id == transaction.id
        )
        .all()
    )

    assert audits == []
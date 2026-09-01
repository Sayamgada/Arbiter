from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.transaction import Transaction
from app.schemas.negotiation import TransactionStatus
from app.services.decision_controller import NDCResult


class TransactionService:
    """
    Owns transaction creation and lifecycle transitions.

    Negotiation determines whether a transaction is allowed.
    This service persists the resulting transaction and controls
    its payment lifecycle.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_from_decision(
        self,
        *,
        buyer_id: int,
        merchant_id: str,
        product_id: int,
        proposed_offer: dict,
        result: NDCResult,
        session_id: str | None = None,
    ) -> Transaction:
        """
        Create a transaction from an NDC decision.

        Approved negotiations enter PAYMENT_PENDING.
        Non-approved negotiations are persisted as CANCELLED.
        """

        status = (
            TransactionStatus.PAYMENT_PENDING.value
            if result.decision.value == "approve"
            else TransactionStatus.CANCELLED.value
        )

        transaction = Transaction(
            transaction_id=f"txn_{uuid4().hex}",
            buyer_id=buyer_id,
            merchant_id=merchant_id,
            product_id=product_id,
            proposed_offer=proposed_offer,
            final_offer={
                "discount_pct": result.discount_pct,
                "discount_value": result.discount_value,
                "final_price": result.final_price,
            },
            decision=result.decision.value,
            status=status,
            razorpay_ref="",
        )

        self.db.add(transaction)
        self.db.flush()

        self._create_audit_log(
            transaction=transaction,
            proposed_offer=proposed_offer,
            result=result,
        )

        self.db.commit()
        self.db.refresh(transaction)

        return transaction

    def update_status(
        self,
        *,
        transaction: Transaction,
        status: TransactionStatus,
        razorpay_ref: str | None = None,
    ) -> Transaction:
        """
        Update the lifecycle state of a transaction.

        This is intentionally centralized so payment integrations
        cannot mutate transaction state arbitrarily.
        """

        self._validate_transition(
            current=transaction.status,
            target=status.value,
        )

        transaction.status = status.value

        if razorpay_ref is not None:
            transaction.razorpay_ref = razorpay_ref

        self.db.commit()
        self.db.refresh(transaction)

        return transaction

    def get_by_transaction_id(
        self,
        transaction_id: str,
    ) -> Transaction | None:
        return (
            self.db.query(Transaction)
            .filter(
                Transaction.transaction_id == transaction_id
            )
            .first()
        )

    def _create_audit_log(
        self,
        *,
        transaction: Transaction,
        proposed_offer: dict,
        result: NDCResult,
    ) -> None:
        audit = AuditLog(
            transaction_id=transaction.id,
            trust_snapshot={
                "score": result.trust_score,
                "authority": result.authority.value,
            },
            bounds_snapshot={
                "decision": result.decision.value,
                "reason": result.reason,
            },
            budget_snapshot={
                "allocated": proposed_offer.get(
                    "allocated_budget"
                ),
                "remaining": result.budget_remaining,
            },
            offer_snapshot={
                "discount_pct": result.discount_pct,
                "discount_value": result.discount_value,
                "final_price": result.final_price,
            },
            decision=result.decision.value,
            reasoning_text=result.reason,
        )

        self.db.add(audit)

    @staticmethod
    def _validate_transition(
        *,
        current: str,
        target: str,
    ) -> None:
        allowed_transitions = {
            TransactionStatus.NEGOTIATING.value: {
                TransactionStatus.ACCEPTED.value,
                TransactionStatus.CANCELLED.value,
            },
            TransactionStatus.ACCEPTED.value: {
                TransactionStatus.PAYMENT_PENDING.value,
                TransactionStatus.CANCELLED.value,
            },
            TransactionStatus.PAYMENT_PENDING.value: {
                TransactionStatus.PAYMENT_CREATED.value,
                TransactionStatus.CANCELLED.value,
            },
            TransactionStatus.PAYMENT_CREATED.value: {
                TransactionStatus.PAYMENT_AUTHORIZED.value,
                TransactionStatus.PAYMENT_FAILED.value,
                TransactionStatus.CANCELLED.value,
            },
            TransactionStatus.PAYMENT_AUTHORIZED.value: {
                TransactionStatus.COMPLETED.value,
                TransactionStatus.PAYMENT_FAILED.value,
            },
            TransactionStatus.COMPLETED.value: set(),
            TransactionStatus.PAYMENT_FAILED.value: set(),
            TransactionStatus.CANCELLED.value: set(),
        }

        if target not in allowed_transitions.get(current, set()):
            raise ValueError(
                f"Invalid transaction status transition: "
                f"{current} -> {target}"
            )
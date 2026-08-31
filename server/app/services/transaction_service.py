from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.transaction import Transaction
from app.services.decision_controller import NDCResult


class TransactionService:
    """Persists negotiation decisions and their audit trail."""

    def __init__(self, db: Session):
        self.db = db

    def record_decision(
        self,
        *,
        buyer_id: int,
        merchant_id: str,
        product_id: int,
        proposed_offer: dict,
        result: NDCResult,
        razorpay_ref: str = "",
    ) -> Transaction:
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
            razorpay_ref=razorpay_ref,
        )

        self.db.add(transaction)
        self.db.flush()

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
        self.db.commit()
        self.db.refresh(transaction)

        return transaction

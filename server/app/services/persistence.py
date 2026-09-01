from sqlalchemy.orm import Session

from app.models import AuditLog, Buyer, Product, Transaction, TrustScoreRecord
from app.schemas.negotiation import BuyerSignals
from app.services.decision_controller import NDCResult


class NegotiationPersistence:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_buyer(
        self,
        buyer_id: str,
        signals: BuyerSignals,
    ) -> Buyer:
        buyer = (
            self.db.query(Buyer)
            .filter(Buyer.buyer_id == buyer_id)
            .first()
        )

        if buyer is None:
            buyer = Buyer(
                buyer_id=buyer_id,
                identity_confidence=signals.identity_confidence,
                intent_confidence=signals.intent_confidence,
                history_score=signals.history_score,
                violation_count=signals.violation_count,
                behavior_score=signals.behavior_score,
                is_active=True,
            )
            self.db.add(buyer)
            self.db.flush()
        else:
            buyer.identity_confidence = signals.identity_confidence
            buyer.intent_confidence = signals.intent_confidence
            buyer.history_score = signals.history_score
            buyer.violation_count = signals.violation_count
            buyer.behavior_score = signals.behavior_score

        return buyer

    def record_decision(
        self,
        *,
        transaction_id: str,
        buyer_id: str,
        session_id: str,
        merchant_id: str,
        product_id: int,
        proposed_offer: dict,
        result: NDCResult,
        signals: BuyerSignals,
        db_product: Product,
    ) -> Transaction:
        buyer = self.get_or_create_buyer(buyer_id, signals)

        trust_record = TrustScoreRecord(
            buyer_id=buyer.id,
            session_id=session_id,
            score=result.trust_score,
            sub_scores={
                "identity": signals.identity_confidence,
                "intent": signals.intent_confidence,
                "history": signals.history_score,
                "violations": signals.violation_count,
                "behavior": signals.behavior_score,
                "authority": result.authority.value,
            },
        )
        self.db.add(trust_record)

        transaction = Transaction(
            transaction_id=transaction_id,
            buyer_id=buyer.id,
            merchant_id=merchant_id,
            product_id=product_id,
            proposed_offer=proposed_offer,
            final_offer={
                "discount_pct": result.discount_pct,
                "discount_value": result.discount_value,
                "final_price": result.final_price,
            },
            decision=result.decision.value,
            razorpay_ref="",
        )
        self.db.add(transaction)
        self.db.flush()

        audit = AuditLog(
            transaction_id=transaction.id,
            trust_snapshot={
                "score": result.trust_score,
                "authority": result.authority.value,
                "sub_scores": {
                    "identity": signals.identity_confidence,
                    "intent": signals.intent_confidence,
                    "history": signals.history_score,
                    "violations": signals.violation_count,
                    "behavior": signals.behavior_score,
                },
            },
            bounds_snapshot={
                "requested_discount_pct": proposed_offer.get(
                    "requested_discount_pct"
                ),
                "max_discount_pct": proposed_offer.get(
                    "max_discount_pct"
                ),
            },
            budget_snapshot={
                "allocated": proposed_offer.get("allocated_budget"),
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

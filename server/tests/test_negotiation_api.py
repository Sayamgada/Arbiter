from app.core.database import SessionLocal
from app.core.redis import get_redis
from app.main import app
from app.models import AuditLog, Buyer, MerchantPolicy, Product, Transaction
from fastapi.testclient import TestClient
from sqlalchemy import select

client = TestClient(app)


def setup_test_data():
    db = SessionLocal()
    policy = MerchantPolicy(
        merchant_id="api-test-merchant",
        max_discount_pct=12,
        daily_budget=5000,
        trust_full_threshold=80,
        trust_restricted_threshold=40,
    )
    buyer = Buyer(
        buyer_id="api-test-buyer",
        identity_confidence=100,
        intent_confidence=100,
        history_score=100,
        violation_count=0,
        behavior_score=100,
        is_active=True,
    )

    product = Product(
        merchant_id="api-test-merchant",
        name="API Test Product",
        description="Integration test product",
        price=10000,
        cost=7000,
        inventory=10,
    )

    db.add(policy)
    db.add(buyer)
    db.add(product)
    db.commit()
    db.refresh(buyer)
    db.refresh(product)

    buyer_id = buyer.buyer_id
    buyer_pk = buyer.id
    product_pk = product.id

    db.close()

    return buyer_id, buyer_pk, product_pk


def cleanup_test_data():
    db = SessionLocal()

    transactions = db.scalars(
        select(Transaction).where(Transaction.merchant_id == "api-test-merchant")
    ).all()

    for transaction in transactions:
        db.query(AuditLog).filter(AuditLog.transaction_id == transaction.id).delete()

    db.query(Transaction).filter(
        Transaction.merchant_id == "api-test-merchant"
    ).delete()

    db.query(Product).filter(Product.merchant_id == "api-test-merchant").delete()
    db.query(MerchantPolicy).filter(
        MerchantPolicy.merchant_id == "api-test-merchant"
    ).delete()
    db.query(Buyer).filter(Buyer.buyer_id == "api-test-buyer").delete()

    db.commit()
    db.close()


def test_unknown_buyer_returns_404():
    cleanup_test_data()

    _, _, product_id = setup_test_data()

    response = client.post(
        "/api/v1/negotiation/decide",
        json={
            "merchant_id": "api-test-merchant",
            "period": "test",
            "buyer_id": "does-not-exist",
            "product_id": product_id,
            "buyer_signals": {
                "identity_confidence": 100,
                "intent_confidence": 100,
                "history_score": 100,
                "violation_count": 0,
                "behavior_score": 100,
            },
            "product_price": 10000,
            "product_cost": 7000,
            "requested_discount_pct": 10,
            "max_discount_pct": 12,
            "allocated_budget": 5000,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Buyer not found"

    cleanup_test_data()


def test_inactive_buyer_returns_403():
    cleanup_test_data()

    buyer_id, _, product_id = setup_test_data()

    db = SessionLocal()
    buyer = db.scalar(select(Buyer).where(Buyer.buyer_id == buyer_id))
    buyer.is_active = False
    db.commit()
    db.close()

    response = client.post(
        "/api/v1/negotiation/decide",
        json={
            "merchant_id": "api-test-merchant",
            "period": "test",
            "buyer_id": buyer_id,
            "product_id": product_id,
            "buyer_signals": {
                "identity_confidence": 100,
                "intent_confidence": 100,
                "history_score": 100,
                "violation_count": 0,
                "behavior_score": 100,
            },
            "product_price": 10000,
            "product_cost": 7000,
            "requested_discount_pct": 10,
            "max_discount_pct": 12,
            "allocated_budget": 5000,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Buyer is inactive"

    cleanup_test_data()


def test_wrong_merchant_product_returns_404():
    cleanup_test_data()

    buyer_id, _, product_id = setup_test_data()

    response = client.post(
        "/api/v1/negotiation/decide",
        json={
            "merchant_id": "wrong-merchant",
            "period": "test",
            "buyer_id": buyer_id,
            "product_id": product_id,
            "buyer_signals": {
                "identity_confidence": 100,
                "intent_confidence": 100,
                "history_score": 100,
                "violation_count": 0,
                "behavior_score": 100,
            },
            "product_price": 10000,
            "product_cost": 7000,
            "requested_discount_pct": 10,
            "max_discount_pct": 12,
            "allocated_budget": 5000,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found for merchant"

    cleanup_test_data()

def test_negotiation_persists_transaction_and_audit():
    cleanup_test_data()
    redis = get_redis()
    redis.flushdb()

    buyer_id, buyer_pk, product_id = setup_test_data()

    response = client.post(
        "/api/v1/negotiation/decide",
        json={
            "merchant_id": "api-test-merchant",
            "period": "test",
            "buyer_id": buyer_id,
            "product_id": product_id,
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

    assert response.status_code == 200

    data = response.json()

    assert data["decision"] == "counter"
    assert data["authority"] == "full"
    assert data["trust_score"] == 100

    assert data["discount_pct"] > 0
    assert data["discount_pct"] < 10
    assert data["discount_pct"] <= 12

    assert data["discount_value"] > 0
    assert data["final_price"] < 10000
    assert data["final_price"] >= 7000

    # A counter does not commit merchant budget.
    assert data["budget_remaining"] == 5000

    assert data["transaction_id"].startswith("txn_")

    db = SessionLocal()

    transaction = db.scalar(
        select(Transaction).where(
            Transaction.transaction_id == data["transaction_id"]
        )
    )

    assert transaction is not None
    assert transaction.buyer_id == buyer_pk
    assert transaction.product_id == product_id
    assert transaction.merchant_id == "api-test-merchant"

    assert transaction.decision == "counter"
    assert transaction.status == "cancelled"

    assert (
        transaction.final_offer["discount_pct"]
        == data["discount_pct"]
    )
    assert (
        transaction.final_offer["final_price"]
        == data["final_price"]
    )

    audit = db.scalar(
        select(AuditLog).where(
            AuditLog.transaction_id == transaction.id
        )
    )

    assert audit is not None
    assert audit.decision == "counter"
    assert audit.trust_snapshot["score"] == 100
    assert audit.trust_snapshot["authority"] == "full"

    # No budget should have been consumed by a hypothetical counter.
    assert audit.budget_snapshot["remaining"] == 5000

    assert (
        audit.offer_snapshot["discount_value"]
        == data["discount_value"]
    )

    db.close()

    cleanup_test_data()


def test_negotiation_session_blocks_low_trust_buyer():
    cleanup_test_data()
    redis = get_redis()
    redis.flushdb()

    buyer_id, _, product_id = setup_test_data()

    response = client.post(
        "/api/v1/negotiation/session",
        json={
            "merchant_id": "api-test-merchant",
            "period": "test",
            "buyer_id": buyer_id,
            "product_id": product_id,
            "buyer_signals": {
                "identity_confidence": 10,
                "intent_confidence": 10,
                "history_score": 10,
                "violation_count": 5,
                "behavior_score": 10,
            },
            "requested_discount_pct": 10,
            "max_rounds": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "blocked"
    assert data["final_price"] is None
    assert data["final_discount_pct"] is None

    cleanup_test_data()


def test_negotiation_session_expires_when_discount_cannot_be_met():
    cleanup_test_data()
    redis = get_redis()
    redis.flushdb()

    buyer_id, _, product_id = setup_test_data()

    response = client.post(
        "/api/v1/negotiation/session",
        json={
            "merchant_id": "api-test-merchant",
            "period": "test",
            "buyer_id": buyer_id,
            "product_id": product_id,
            "buyer_signals": {
                "identity_confidence": 100,
                "intent_confidence": 100,
                "history_score": 100,
                "violation_count": 0,
                "behavior_score": 100,
            },
            "requested_discount_pct": 20,
            "max_rounds": 3,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "expired"
    assert data["rounds"] == 3
    assert data["final_price"] is None
    assert data["final_discount_pct"] is None

    cleanup_test_data()
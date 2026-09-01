import pytest

from app.core.database import SessionLocal
from app.models.audit import AuditLog
from app.models.buyer import Buyer
from app.models.product import Product
from app.models.transaction import Transaction


@pytest.fixture
def db_session():
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()

        session.query(AuditLog).delete()
        session.query(Transaction).delete()
        session.query(Product).delete()
        session.query(Buyer).delete()

        session.commit()
        session.close()


@pytest.fixture
def transaction_dependencies(db_session):
    buyer = Buyer(
        buyer_id="test-buyer",
        identity_confidence=100,
        intent_confidence=100,
        history_score=100,
        violation_count=0,
        behavior_score=100,
        is_active=True,
    )

    product = Product(
        merchant_id="test-merchant",
        name="Test Product",
        description="Test product",
        price=1000,
        cost=700,
        inventory=10,
    )

    db_session.add_all([buyer, product])
    db_session.commit()

    db_session.refresh(buyer)
    db_session.refresh(product)

    return buyer, product
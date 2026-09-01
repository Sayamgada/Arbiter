import pytest

from app.core.database import SessionLocal
from app.models.audit import AuditLog
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

        session.commit()
        session.close()
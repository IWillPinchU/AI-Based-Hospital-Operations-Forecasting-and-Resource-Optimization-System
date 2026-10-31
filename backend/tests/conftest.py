import sys
import os
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend root is on Python sys.path so app and scripts can be imported
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.database import Base, OperationalMetrics


from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="session")
def test_engine():
    """Session-wide in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Function-scoped clean database session that supports commit and cleans up rows after test."""
    Session = sessionmaker(bind=test_engine)
    session = Session()

    yield session

    session.close()
    with test_engine.connect() as conn:
        conn.execute(OperationalMetrics.__table__.delete())
        conn.commit()


@pytest.fixture
def sample_operational_record():
    """Provides a sample valid operational metric dictionary."""
    return {
        "timestamp": datetime(2026, 10, 29, 14, 0, 0, tzinfo=timezone.utc),
        "ed_arrivals": 57,
        "ed_patients": 46,
        "available_beds": 42,
        "icu_occupancy_pct": 87.0,
        "nurses_available": 10,
        "doctors_available": 4,
    }


@pytest.fixture
def client(test_engine, db_session):
    """FastAPI TestClient with database session dependency overridden to use the test session."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

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


@pytest.fixture(scope="session")
def test_engine():
    """Session-wide in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Function-scoped clean database session."""
    connection = test_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


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

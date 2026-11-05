import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, Float, DateTime, String, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import DATABASE_URL

# SQLite requires connect_args check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class OperationalMetrics(Base):
    __tablename__ = "operational_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), unique=True, index=True, nullable=False)
    ed_arrivals = Column(Integer, nullable=False)
    ed_patients = Column(Integer, nullable=False)
    available_beds = Column(Integer, nullable=False)
    icu_occupancy_pct = Column(Float, nullable=False)
    nurses_available = Column(Integer, nullable=False)  # ED-only active nurses on duty
    doctors_available = Column(Integer, nullable=False)  # ED-only active doctors on duty
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AnomalyEvent(Base):
    """Persisted anomaly detection event for historical auditing and alert tracking."""
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), unique=True, index=True, nullable=False)
    observed_value = Column(Integer, nullable=False)
    expected_baseline = Column(Float, nullable=False)
    deviation_pct = Column(Float, nullable=False)
    severity = Column(String(50), nullable=False)
    explanation = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


def init_db():
    """Initializes tables in database at startup without migrations."""
    if DATABASE_URL.startswith("sqlite"):
        # Ensure target directory exists for SQLite
        raw_path = DATABASE_URL.replace("sqlite:////", "/").replace("sqlite:///", "")
        if "/" in raw_path or "\\" in raw_path:
            db_dir = os.path.dirname(raw_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency generator yielding an active database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

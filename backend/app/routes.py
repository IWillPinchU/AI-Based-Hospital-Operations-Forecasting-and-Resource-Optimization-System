from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion import ingest_operational_csv
from app.state import get_current_hospital_state
from app.forecast import get_ed_forecast
from app.anomaly import detect_ed_anomalies
from app.optimizer import get_resource_recommendations
from app.schemas import (
    IngestionResponse,
    CurrentStateResponse,
    ForecastResponse,
    AnomalyResponse,
    RecommendationResponse,
)

router = APIRouter(prefix="/api/v1")


@router.post("/ingest/csv", response_model=IngestionResponse, tags=["Ingestion"])
def upload_operational_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Ingests a CSV containing hourly operational metrics with idempotent upsert."""
    return ingest_operational_csv(file, db)


@router.get("/current-state", response_model=CurrentStateResponse, tags=["Layer 1"])
def read_current_state(db: Session = Depends(get_db)):
    """Layer 1: Returns the latest operational hospital state and load ratios."""
    return get_current_hospital_state(db)


@router.get("/forecast", response_model=ForecastResponse, tags=["Layer 2"])
def read_ed_forecast(db: Session = Depends(get_db)):
    """Layer 2: Returns next-hour ED arrival prediction using 25-hour lags."""
    return get_ed_forecast(db)


@router.get("/anomalies", response_model=AnomalyResponse, tags=["Layer 3"])
def read_ed_anomalies(db: Session = Depends(get_db)):
    """Layer 3: Compares current ED arrivals against historical hour-of-week baseline."""
    return detect_ed_anomalies(db)


@router.get("/recommendations", response_model=RecommendationResponse, tags=["Layer 4"])
def read_resource_recommendations(db: Session = Depends(get_db)):
    """Layer 4: Returns advisory nurse staffing and bed turnover adjustments."""
    return get_resource_recommendations(db)

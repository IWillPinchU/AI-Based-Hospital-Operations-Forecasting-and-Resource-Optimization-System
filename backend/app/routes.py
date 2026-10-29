from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion import ingest_operational_csv
from app.state import get_current_hospital_state
from app.schemas import IngestionResponse, CurrentStateResponse

router = APIRouter(prefix="/api/v1")


@router.post("/ingest/csv", response_model=IngestionResponse, tags=["Ingestion"])
def upload_operational_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Ingests a CSV containing hourly operational metrics with idempotent upsert."""
    return ingest_operational_csv(file, db)


@router.get("/current-state", response_model=CurrentStateResponse, tags=["Layer 1"])
def read_current_state(db: Session = Depends(get_db)):
    """Layer 1: Returns the latest operational hospital state and load ratios."""
    return get_current_hospital_state(db)

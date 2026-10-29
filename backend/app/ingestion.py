import io
from datetime import datetime, timezone
import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import OperationalMetrics
from app.schemas import IngestionResponse, OperationalRowSchema

REQUIRED_COLUMNS = [
    "timestamp",
    "ed_arrivals",
    "ed_patients",
    "available_beds",
    "icu_occupancy_pct",
    "nurses_available",
    "doctors_available",
]


def parse_and_validate_csv(file_bytes: bytes) -> pd.DataFrame:
    """Parses raw CSV bytes, checks column presence, and validates data formats."""
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse CSV file: {str(e)}",
        )

    # Check for missing required columns
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"CSV missing required columns: {missing}",
        )

    if df.empty:
        raise HTTPException(
            status_code=422,
            detail="CSV file contains no operational data rows.",
        )

    # Validate timestamps
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid timestamp format in CSV: {str(e)}",
        )

    # Validate numerical types and ranges
    for idx, row in df.iterrows():
        try:
            # Pydantic validation for each row
            OperationalRowSchema(
                timestamp=row["timestamp"].to_pydatetime(),
                ed_arrivals=int(row["ed_arrivals"]),
                ed_patients=int(row["ed_patients"]),
                available_beds=int(row["available_beds"]),
                icu_occupancy_pct=float(row["icu_occupancy_pct"]),
                nurses_available=int(row["nurses_available"]),
                doctors_available=int(row["doctors_available"]),
            )
        except Exception as val_err:
            raise HTTPException(
                status_code=422,
                detail=f"Validation failed on CSV row {idx + 1}: {str(val_err)}",
            )

    return df


def ingest_operational_csv(file: UploadFile, db: Session) -> IngestionResponse:
    """Reads uploaded CSV and performs idempotent chronological upsert into SQLite."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=422,
            detail="Invalid file format. Only .csv files are supported.",
        )

    try:
        file_bytes = file.file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading uploaded file: {str(e)}")

    df = parse_and_validate_csv(file_bytes)
    df = df.sort_values("timestamp").reset_index(drop=True)

    rows_processed = len(df)
    rows_inserted = 0
    rows_updated = 0

    # Normalize to UTC-aware datetime for robust comparison across database dialects (SQLite/PostgreSQL)
    def normalize_utc(dt: datetime) -> datetime:
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)

    # Query all existing records to do efficient idempotent upsert
    existing_records = {
        normalize_utc(rec.timestamp): rec
        for rec in db.query(OperationalMetrics).all()
    }

    latest_ts = None

    for _, row in df.iterrows():
        ts = row["timestamp"].to_pydatetime()
        ts_norm = normalize_utc(ts)
        latest_ts = ts if latest_ts is None or ts > latest_ts else latest_ts

        # Match by UTC timestamp
        if ts_norm in existing_records:
            # Idempotent update of existing record
            existing = existing_records[ts_norm]
            existing.ed_arrivals = int(row["ed_arrivals"])
            existing.ed_patients = int(row["ed_patients"])
            existing.available_beds = int(row["available_beds"])
            existing.icu_occupancy_pct = float(row["icu_occupancy_pct"])
            existing.nurses_available = int(row["nurses_available"])
            existing.doctors_available = int(row["doctors_available"])
            rows_updated += 1
        else:
            # Insert new record
            new_record = OperationalMetrics(
                timestamp=ts,
                ed_arrivals=int(row["ed_arrivals"]),
                ed_patients=int(row["ed_patients"]),
                available_beds=int(row["available_beds"]),
                icu_occupancy_pct=float(row["icu_occupancy_pct"]),
                nurses_available=int(row["nurses_available"]),
                doctors_available=int(row["doctors_available"]),
            )
            db.add(new_record)
            existing_records[ts_norm] = new_record
            rows_inserted += 1

    db.commit()

    return IngestionResponse(
        status="success",
        filename=file.filename,
        rows_processed=rows_processed,
        rows_inserted=rows_inserted,
        rows_updated=rows_updated,
        latest_timestamp=latest_ts,
    )

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import OperationalMetrics
from app.schemas import CurrentStateResponse, DepartmentMetrics


def get_current_hospital_state(db: Session) -> CurrentStateResponse:
    """Layer 1: Queries the latest operational record and computes current department metrics."""
    latest = (
        db.query(OperationalMetrics)
        .order_by(desc(OperationalMetrics.timestamp))
        .first()
    )

    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No operational data available. Please upload an operational CSV first.",
        )

    # Compute operational ratios (guarded against division by zero)
    nurse_ratio = round(latest.ed_patients / max(latest.nurses_available, 1), 2)
    doctor_ratio = round(latest.ed_patients / max(latest.doctors_available, 1), 2)

    from datetime import timezone
    ts = latest.timestamp.replace(tzinfo=timezone.utc) if latest.timestamp.tzinfo is None else latest.timestamp.astimezone(timezone.utc)

    return CurrentStateResponse(
        timestamp=ts,
        ed_arrivals=latest.ed_arrivals,
        ed_patients=latest.ed_patients,
        available_beds=latest.available_beds,
        icu_occupancy_pct=latest.icu_occupancy_pct,
        nurses_available=latest.nurses_available,
        doctors_available=latest.doctors_available,
        metrics=DepartmentMetrics(
            patient_to_nurse_ratio=nurse_ratio,
            patient_to_doctor_ratio=doctor_ratio,
        ),
    )

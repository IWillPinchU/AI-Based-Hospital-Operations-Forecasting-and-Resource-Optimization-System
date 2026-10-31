from datetime import timezone
from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import (
    ANOMALY_CRITICAL_SURGE_PCT,
    ANOMALY_MODERATE_SURGE_PCT,
    ANOMALY_MODERATE_DROP_PCT,
    ANOMALY_UNUSUAL_DROP_PCT,
)
from app.database import OperationalMetrics
from app.schemas import AnomalyResponse


def detect_ed_anomalies(db: Session) -> AnomalyResponse:
    """Layer 3: Detects unusual arrival surges/drops against historical hour-of-week baseline."""
    # 1. Fetch latest record
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

    # 2. Query historical rows excluding the current observation
    historical_rows = (
        db.query(OperationalMetrics)
        .filter(OperationalMetrics.timestamp < latest.timestamp)
        .all()
    )

    # 3. Filter for matching hour-of-week bin (day_of_week, hour_of_day)
    target_weekday = latest.timestamp.weekday()
    target_hour = latest.timestamp.hour

    matching_history = [
        r.ed_arrivals
        for r in historical_rows
        if r.timestamp.weekday() == target_weekday and r.timestamp.hour == target_hour
    ]

    # Failure behavior: If count is 0 or baseline mean is 0, return HTTP 400
    if not matching_history:
        raise HTTPException(
            status_code=400,
            detail="Insufficient historical data to compute baseline for this time period.",
        )

    baseline = sum(matching_history) / len(matching_history)
    if baseline == 0:
        raise HTTPException(
            status_code=400,
            detail="Insufficient historical data to compute baseline for this time period.",
        )

    # 4. Compute deviation percentage
    observed = latest.ed_arrivals
    deviation_pct = round(((observed - baseline) / baseline) * 100.0, 1)
    expected_baseline = round(baseline, 1)

    # 5. Classify severity using named thresholds from app/config.py
    if deviation_pct >= ANOMALY_CRITICAL_SURGE_PCT:
        severity = "CRITICAL_SURGE"
        is_anomaly = True
    elif deviation_pct >= ANOMALY_MODERATE_SURGE_PCT:
        severity = "MODERATE_SURGE"
        is_anomaly = True
    elif deviation_pct > ANOMALY_MODERATE_DROP_PCT:
        severity = "NORMAL"
        is_anomaly = False
    elif deviation_pct > ANOMALY_UNUSUAL_DROP_PCT:
        severity = "MODERATE_DROP"
        is_anomaly = True
    else:
        severity = "UNUSUAL_DROP"
        is_anomaly = True

    # 6. Construct explanation
    day_name = latest.timestamp.strftime("%A")
    time_str = latest.timestamp.strftime("%H:%M")
    direction = "above" if deviation_pct >= 0 else "below"
    explanation = (
        f"ED arrivals ({observed}) are {abs(deviation_pct):.1f}% {direction} "
        f"the historical {day_name} {time_str} baseline ({expected_baseline:.1f})."
    )

    ts = (
        latest.timestamp.replace(tzinfo=timezone.utc)
        if latest.timestamp.tzinfo is None
        else latest.timestamp.astimezone(timezone.utc)
    )

    return AnomalyResponse(
        timestamp=ts,
        observed_value=observed,
        expected_baseline=expected_baseline,
        deviation_pct=deviation_pct,
        is_anomaly=is_anomaly,
        severity=severity,
        explanation=explanation,
    )

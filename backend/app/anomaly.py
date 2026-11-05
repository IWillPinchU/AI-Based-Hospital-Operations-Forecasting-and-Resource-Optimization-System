from datetime import datetime, timezone
from typing import Optional, List
from collections import defaultdict
from fastapi import HTTPException
from sqlalchemy import desc, extract
from sqlalchemy.orm import Session

from app.config import (
    ANOMALY_CRITICAL_SURGE_PCT,
    ANOMALY_MODERATE_SURGE_PCT,
    ANOMALY_MODERATE_DROP_PCT,
    ANOMALY_UNUSUAL_DROP_PCT,
)
from app.database import OperationalMetrics, AnomalyEvent
from app.schemas import (
    AnomalyResponse,
    AnomalyEventSchema,
    AnomalyStatsSummary,
    AnomalyHistoryResponse,
    AnomalyResolveResponse,
)
from app.utils import to_utc


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

    # 2. Query only matching historical hour-of-week rows at the database level
    target_hour = latest.timestamp.hour
    target_dow = int(latest.timestamp.strftime("%w"))

    matching_history = [
        val[0]
        for val in (
            db.query(OperationalMetrics.ed_arrivals)
            .filter(
                OperationalMetrics.timestamp < latest.timestamp,
                extract("hour", OperationalMetrics.timestamp) == target_hour,
                extract("dow", OperationalMetrics.timestamp) == target_dow,
            )
            .all()
        )
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

    ts = to_utc(latest.timestamp)

    # 7. Persist detected anomalies to the alert log if not already recorded
    if is_anomaly:
        existing = db.query(AnomalyEvent).filter(AnomalyEvent.timestamp == ts).first()
        if not existing:
            event = AnomalyEvent(
                timestamp=ts,
                observed_value=observed,
                expected_baseline=expected_baseline,
                deviation_pct=deviation_pct,
                severity=severity,
                explanation=explanation,
                resolved=False,
            )
            db.add(event)
            db.commit()

    return AnomalyResponse(
        timestamp=ts,
        observed_value=observed,
        expected_baseline=expected_baseline,
        deviation_pct=deviation_pct,
        is_anomaly=is_anomaly,
        severity=severity,
        explanation=explanation,
    )


def get_anomaly_history(
    db: Session,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 50,
) -> AnomalyHistoryResponse:
    """Returns chronologically ordered anomaly history log with filtering and summary metrics."""
    all_events = db.query(AnomalyEvent).all()
    critical_count = sum(1 for e in all_events if e.severity == "CRITICAL_SURGE")
    moderate_count = sum(1 for e in all_events if e.severity == "MODERATE_SURGE")
    drops_count = sum(1 for e in all_events if "DROP" in e.severity)
    unresolved_count = sum(1 for e in all_events if not e.resolved)
    resolved_count = sum(1 for e in all_events if e.resolved)

    summary = AnomalyStatsSummary(
        total_anomalies=len(all_events),
        critical_surges=critical_count,
        moderate_surges=moderate_count,
        drops=drops_count,
        unresolved_count=unresolved_count,
        resolved_count=resolved_count,
    )

    query = db.query(AnomalyEvent)
    if severity:
        query = query.filter(AnomalyEvent.severity == severity.upper())
    if resolved is not None:
        query = query.filter(AnomalyEvent.resolved == resolved)

    events = query.order_by(desc(AnomalyEvent.timestamp)).limit(limit).all()

    event_schemas = [
        AnomalyEventSchema(
            id=e.id,
            timestamp=to_utc(e.timestamp),
            observed_value=e.observed_value,
            expected_baseline=e.expected_baseline,
            deviation_pct=e.deviation_pct,
            severity=e.severity,
            explanation=e.explanation,
            resolved=e.resolved,
            resolved_at=to_utc(e.resolved_at) if e.resolved_at else None,
            created_at=to_utc(e.created_at),
        )
        for e in events
    ]

    return AnomalyHistoryResponse(events=event_schemas, summary=summary)


def resolve_anomaly_event(
    db: Session,
    event_id: int,
    resolved: bool = True,
) -> AnomalyResolveResponse:
    """Updates the resolved / acknowledged status of an anomaly event."""
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Anomaly alert event with ID {event_id} not found.",
        )

    event.resolved = resolved
    event.resolved_at = datetime.now(timezone.utc) if resolved else None
    db.commit()

    return AnomalyResolveResponse(
        id=event.id,
        resolved=event.resolved,
        resolved_at=to_utc(event.resolved_at) if event.resolved_at else None,
        status="resolved" if event.resolved else "unresolved",
    )


def scan_and_record_all_anomalies(db: Session) -> int:
    """Scans all historical operational rows, computes historical hour-of-week baselines, and records anomaly events."""
    rows = (
        db.query(OperationalMetrics)
        .order_by(OperationalMetrics.timestamp.asc())
        .all()
    )
    if len(rows) < 24:
        return 0

    new_anomalies_count = 0
    history_by_bin = defaultdict(list)

    for row in rows:
        ts = to_utc(row.timestamp)
        h = ts.hour
        dow = int(ts.strftime("%w"))
        past_values = history_by_bin[(dow, h)]

        if past_values:
            baseline = sum(past_values) / len(past_values)
            if baseline > 0:
                deviation_pct = round(((row.ed_arrivals - baseline) / baseline) * 100.0, 1)
                severity = None
                is_anomaly = False

                if deviation_pct >= ANOMALY_CRITICAL_SURGE_PCT:
                    severity = "CRITICAL_SURGE"
                    is_anomaly = True
                elif deviation_pct >= ANOMALY_MODERATE_SURGE_PCT:
                    severity = "MODERATE_SURGE"
                    is_anomaly = True
                elif deviation_pct < ANOMALY_UNUSUAL_DROP_PCT:
                    severity = "UNUSUAL_DROP"
                    is_anomaly = True
                elif deviation_pct <= ANOMALY_MODERATE_DROP_PCT:
                    severity = "MODERATE_DROP"
                    is_anomaly = True

                if is_anomaly and severity:
                    existing = (
                        db.query(AnomalyEvent)
                        .filter(AnomalyEvent.timestamp == ts)
                        .first()
                    )
                    if not existing:
                        day_name = ts.strftime("%A")
                        time_str = ts.strftime("%H:%M")
                        direction = "above" if deviation_pct >= 0 else "below"
                        explanation = (
                            f"ED arrivals ({row.ed_arrivals}) were {abs(deviation_pct):.1f}% {direction} "
                            f"the historical {day_name} {time_str} baseline ({round(baseline, 1)})."
                        )
                        db.add(
                            AnomalyEvent(
                                timestamp=ts,
                                observed_value=row.ed_arrivals,
                                expected_baseline=round(baseline, 1),
                                deviation_pct=deviation_pct,
                                severity=severity,
                                explanation=explanation,
                                resolved=False,
                            )
                        )
                        new_anomalies_count += 1

        history_by_bin[(dow, h)].append(row.ed_arrivals)

    if new_anomalies_count > 0:
        db.commit()

    return new_anomalies_count


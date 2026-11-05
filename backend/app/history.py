from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
import numpy as np

from app.database import OperationalMetrics
from app.utils import to_utc
from app.schemas import (
    HistoricalRecord,
    MetricSummary,
    HistoricalSummary,
    HistoricalResponse,
)


def get_historical_telemetry(
    db: Session,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 720,
) -> HistoricalResponse:
    """Queries historical operational telemetry rows within an optional UTC time window."""
    query = db.query(OperationalMetrics)

    start_utc = to_utc(start) if start is not None else None
    end_utc = to_utc(end) if end is not None else None

    if start_utc is not None:
        query = query.filter(OperationalMetrics.timestamp >= start_utc)
    if end_utc is not None:
        query = query.filter(OperationalMetrics.timestamp <= end_utc)

    # When no explicit time range is supplied, fetch the most recent rows
    if start_utc is None and end_utc is None:
        rows = (
            query.order_by(desc(OperationalMetrics.timestamp))
            .limit(min(limit, 2000))
            .all()
        )
        rows.reverse()  # Return chronologically ascending
    else:
        rows = (
            query.order_by(asc(OperationalMetrics.timestamp))
            .limit(min(limit, 2000))
            .all()
        )

    if not rows:
        return HistoricalResponse(records=[], summary=None)

    arrivals = [r.ed_arrivals for r in rows]
    patients = [r.ed_patients for r in rows]
    beds = [r.available_beds for r in rows]
    icu = [r.icu_occupancy_pct for r in rows]

    peak_idx = int(np.argmax(arrivals))
    peak_record = rows[peak_idx]

    summary = HistoricalSummary(
        total_records=len(rows),
        start_timestamp=to_utc(rows[0].timestamp),
        end_timestamp=to_utc(rows[-1].timestamp),
        peak_arrival_timestamp=to_utc(peak_record.timestamp),
        peak_arrivals=int(arrivals[peak_idx]),
        ed_arrivals=MetricSummary(
            min=float(np.min(arrivals)),
            max=float(np.max(arrivals)),
            avg=round(float(np.mean(arrivals)), 2),
            total=float(np.sum(arrivals)),
        ),
        ed_patients=MetricSummary(
            min=float(np.min(patients)),
            max=float(np.max(patients)),
            avg=round(float(np.mean(patients)), 2),
        ),
        available_beds=MetricSummary(
            min=float(np.min(beds)),
            max=float(np.max(beds)),
            avg=round(float(np.mean(beds)), 2),
        ),
        icu_occupancy_pct=MetricSummary(
            min=round(float(np.min(icu)), 2),
            max=round(float(np.max(icu)), 2),
            avg=round(float(np.mean(icu)), 2),
        ),
    )

    records = [
        HistoricalRecord(
            timestamp=to_utc(r.timestamp),
            ed_arrivals=r.ed_arrivals,
            ed_patients=r.ed_patients,
            available_beds=r.available_beds,
            icu_occupancy_pct=r.icu_occupancy_pct,
            nurses_available=r.nurses_available,
            doctors_available=r.doctors_available,
        )
        for r in rows
    ]

    return HistoricalResponse(records=records, summary=summary)


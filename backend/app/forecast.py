import os
from datetime import timedelta, timezone
import joblib
import pandas as pd
from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import OperationalMetrics
from app.schemas import ForecastResponse, HourlyArrival, ModelMetadata

MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models", "ed_forecaster.joblib")
)


def get_ed_forecast(db: Session, model_path: str = MODEL_PATH) -> ForecastResponse:
    """Layer 2: Predicts next-hour ED arrivals using ed_forecaster.joblib and 25-hour lags."""
    # 1. Verify model artifact exists
    if not os.path.exists(model_path):
        raise HTTPException(
            status_code=400,
            detail="Model not trained. Run train_forecaster.py first",
        )

    # 2. Fetch latest 25 rows for lag features (t, t-1, t-24)
    rows = (
        db.query(OperationalMetrics)
        .order_by(desc(OperationalMetrics.timestamp))
        .limit(25)
        .all()
    )

    if len(rows) < 25:
        raise HTTPException(
            status_code=400,
            detail="Insufficient lag data. Upload at least 25 hours of operational data.",
        )

    def _utc(dt):
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)

    for newer, older in zip(rows, rows[1:]):
        if _utc(newer.timestamp) - _utc(older.timestamp) != timedelta(hours=1):
            raise HTTPException(
                status_code=400,
                detail="Data has a gap in the last 25 hours; upload or send the missing hours",
            )

    latest = rows[0]
    lag_1 = rows[1]
    lag_24 = rows[24]

    # 3. Construct 5-feature vector matching training schema
    features = pd.DataFrame(
        [
            {
                "hour_of_day": latest.timestamp.hour,
                "day_of_week": latest.timestamp.weekday(),
                "y_t": latest.ed_arrivals,
                "y_t_minus_1": lag_1.ed_arrivals,
                "y_t_minus_24": lag_24.ed_arrivals,
            }
        ]
    )

    # 4. Model inference
    try:
        model = joblib.load(model_path)
        pred = float(model.predict(features)[0])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Forecasting model inference failed: {str(e)}",
        )

    predicted_ed_arrivals = round(max(0.0, pred), 1)
    expected_net_change = round(predicted_ed_arrivals - latest.ed_arrivals, 1)

    target_ts = latest.timestamp + timedelta(hours=1)
    if target_ts.tzinfo is None:
        target_ts = target_ts.replace(tzinfo=timezone.utc)
    else:
        target_ts = target_ts.astimezone(timezone.utc)

    # 24 most recent observed values, oldest first
    recent_arrivals = [
        HourlyArrival(
            timestamp=(
                r.timestamp.replace(tzinfo=timezone.utc)
                if r.timestamp.tzinfo is None
                else r.timestamp.astimezone(timezone.utc)
            ),
            arrivals=r.ed_arrivals,
        )
        for r in reversed(rows[:24])
    ]

    return ForecastResponse(
        target_timestamp=target_ts,
        current_ed_arrivals=latest.ed_arrivals,
        predicted_ed_arrivals=predicted_ed_arrivals,
        expected_net_change=expected_net_change,
        recent_arrivals=recent_arrivals,
        model_metadata=ModelMetadata(
            model_name="HistGradientBoostingRegressor",
            version="1.0.0",
        ),
    )

import os
from datetime import timedelta, timezone
import joblib
import pandas as pd
from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import OperationalMetrics
from app.schemas import ForecastResponse, HourlyArrival, ModelMetadata
from app.utils import to_utc

MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models", "ed_forecaster.joblib")
)

# In-memory model cache: maps file path to (mtime, model_instance)
_model_cache: dict[str, tuple[float, object]] = {}


def load_cached_model(path: str):
    """Loads a serialized model from path, caching in memory until mtime changes."""
    mtime = os.path.getmtime(path)
    if path in _model_cache:
        cached_mtime, model = _model_cache[path]
        if cached_mtime == mtime:
            return model

    model = joblib.load(path)
    _model_cache[path] = (mtime, model)
    return model


def clear_model_cache():
    """Clears the in-memory model cache (useful in tests or hot-reloading)."""
    _model_cache.clear()


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

    for newer, older in zip(rows, rows[1:]):
        if to_utc(newer.timestamp) - to_utc(older.timestamp) != timedelta(hours=1):
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
        model = load_cached_model(model_path)
        pred = float(model.predict(features)[0])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Forecasting model inference failed: {str(e)}",
        )

    predicted_ed_arrivals = round(max(0.0, pred), 1)
    expected_net_change = round(predicted_ed_arrivals - latest.ed_arrivals, 1)

    target_ts = to_utc(latest.timestamp + timedelta(hours=1))

    # 24 most recent observed values, oldest first
    recent_arrivals = [
        HourlyArrival(
            timestamp=to_utc(r.timestamp),
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

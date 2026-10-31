import os
import joblib
import pytest
import pandas as pd
from datetime import datetime, timezone
from app.database import OperationalMetrics, init_db, engine
from scripts.generate_synthetic_data import generate_synthetic_data
from scripts.train_forecaster import train_forecaster, build_forecasting_dataset


def test_database_initialization(db_session, sample_operational_record):
    """REQ-003: Verify OperationalMetrics table is initialized and supports inserts/queries."""
    # Insert record
    metric = OperationalMetrics(**sample_operational_record)
    db_session.add(metric)
    db_session.commit()

    # Query back
    queried = db_session.query(OperationalMetrics).filter_by(ed_arrivals=57).first()
    assert queried is not None
    assert queried.ed_patients == 46
    assert queried.available_beds == 42
    assert queried.icu_occupancy_pct == 87.0
    assert queried.nurses_available == 10
    assert queried.doctors_available == 4


def test_synthetic_data_generation(tmp_path):
    """REQ-008: Verify synthetic generator produces deterministic output with all 7 schema fields."""
    output_file = str(tmp_path / "synthetic_test.csv")

    df1 = generate_synthetic_data(days=3, seed=42)
    df1.to_csv(output_file, index=False)

    df_loaded = pd.read_csv(output_file)
    expected_cols = [
        "timestamp",
        "ed_arrivals",
        "ed_patients",
        "available_beds",
        "icu_occupancy_pct",
        "nurses_available",
        "doctors_available",
    ]
    assert list(df_loaded.columns) == expected_cols
    assert len(df_loaded) == 3 * 24

    # Verify seed reproducibility (bit-exact match)
    df2 = generate_synthetic_data(days=3, seed=42)
    pd.testing.assert_frame_equal(df1, df2)

    # Check non-negative constraints & valid ICU occupancy range
    assert (df_loaded["ed_arrivals"] >= 0).all()
    assert (df_loaded["ed_patients"] >= 0).all()
    assert (df_loaded["available_beds"] >= 0).all()
    assert (df_loaded["nurses_available"] >= 0).all()
    assert (df_loaded["doctors_available"] >= 0).all()
    assert (df_loaded["icu_occupancy_pct"] >= 0.0).all()
    assert (df_loaded["icu_occupancy_pct"] <= 100.0).all()


def test_model_training_artifact(tmp_path):
    """REQ-009: Verify training script extracts 5 features, trains regressor, and serializes joblib."""
    # Generate 14 days of data for quick training test
    df = generate_synthetic_data(days=14, seed=42)
    data_path = str(tmp_path / "train_data.csv")
    df.to_csv(data_path, index=False)

    model_path = str(tmp_path / "models" / "test_forecaster.joblib")

    # Run training
    model, mae, rmse = train_forecaster(data_path, model_path)

    # Assert artifact exists and is loadable
    assert os.path.exists(model_path)
    loaded_model = joblib.load(model_path)
    assert loaded_model is not None

    # Proposed target: MAE < 5.0
    assert mae < 5.0

    # Test prediction on a sample 5-feature vector: [hour, day_of_week, y_t, y_t_minus_1, y_t_minus_24]
    sample_features = pd.DataFrame([{
        "hour_of_day": 14,
        "day_of_week": 3,
        "y_t": 57,
        "y_t_minus_1": 52,
        "y_t_minus_24": 48,
    }])
    pred = loaded_model.predict(sample_features)[0]
    assert isinstance(float(pred), float)
    assert pred > 0


def test_layer_2_forecast_missing_model_and_insufficient_lags(db_session, tmp_path):
    """REQ-005: Returns HTTP 400 when model is missing or when <25 hours of data exist."""
    from datetime import timedelta
    from fastapi import HTTPException
    from app.forecast import get_ed_forecast

    # 1. Missing model test
    non_existent_model = str(tmp_path / "no_model.joblib")
    with pytest.raises(HTTPException) as exc_info:
        get_ed_forecast(db_session, model_path=non_existent_model)
    assert exc_info.value.status_code == 400
    assert "Model not trained" in exc_info.value.detail

    # 2. Insufficient lags (<25 rows)
    base_time = datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(10):
        db_session.add(
            OperationalMetrics(
                timestamp=base_time + timedelta(hours=i),
                ed_arrivals=30,
                ed_patients=20,
                available_beds=50,
                icu_occupancy_pct=70.0,
                nurses_available=8,
                doctors_available=3,
            )
        )
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info_lag:
        get_ed_forecast(db_session)
    assert exc_info_lag.value.status_code == 400
    assert "Insufficient lag data" in exc_info_lag.value.detail


def test_layer_2_forecast_inference_success(db_session, client):
    """REQ-005: Generates valid next-hour forecast given >=25 hours of data and trained model."""
    from datetime import timedelta
    from app.forecast import get_ed_forecast

    base_time = datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(26):
        db_session.add(
            OperationalMetrics(
                timestamp=base_time + timedelta(hours=i),
                ed_arrivals=20 + i,
                ed_patients=15 + i,
                available_beds=50,
                icu_occupancy_pct=75.0,
                nurses_available=8,
                doctors_available=3,
            )
        )
    db_session.commit()

    # Direct function call
    forecast = get_ed_forecast(db_session)
    assert forecast.current_ed_arrivals == 20 + 25
    assert forecast.predicted_ed_arrivals >= 0.0
    assert forecast.expected_net_change == round(forecast.predicted_ed_arrivals - forecast.current_ed_arrivals, 1)
    assert forecast.target_timestamp == base_time + timedelta(hours=26)
    assert forecast.model_metadata.model_name == "HistGradientBoostingRegressor"

    # API endpoint call via client
    response = client.get("/api/v1/forecast")
    assert response.status_code == 200
    data = response.json()
    assert data["target_timestamp"].endswith("Z")
    assert data["current_ed_arrivals"] == 20 + 25
    assert data["predicted_ed_arrivals"] == forecast.predicted_ed_arrivals
    assert data["expected_net_change"] == forecast.expected_net_change


def test_layer_3_anomaly_no_data_and_zero_baseline(db_session):
    """REQ-006: Returns HTTP 400 when no historical matching hour exists or baseline mean is 0."""
    from datetime import timedelta
    from fastapi import HTTPException
    from app.anomaly import detect_ed_anomalies

    # 1. No data at all -> 404
    with pytest.raises(HTTPException) as exc_404:
        detect_ed_anomalies(db_session)
    assert exc_404.value.status_code == 404

    # 2. Only 1 row (no historical rows before it) -> HTTP 400
    ts = datetime(2026, 10, 29, 14, 0, 0, tzinfo=timezone.utc)
    db_session.add(
        OperationalMetrics(
            timestamp=ts,
            ed_arrivals=50,
            ed_patients=30,
            available_beds=40,
            icu_occupancy_pct=80.0,
            nurses_available=10,
            doctors_available=4,
        )
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc_no_hist:
        detect_ed_anomalies(db_session)
    assert exc_no_hist.value.status_code == 400
    assert "Insufficient historical data" in exc_no_hist.value.detail

    # 3. Historical matching hour has ed_arrivals = 0 (baseline mean == 0) -> HTTP 400
    ts_hist = ts - timedelta(days=7)
    db_session.add(
        OperationalMetrics(
            timestamp=ts_hist,
            ed_arrivals=0,
            ed_patients=30,
            available_beds=40,
            icu_occupancy_pct=80.0,
            nurses_available=10,
            doctors_available=4,
        )
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc_zero_base:
        detect_ed_anomalies(db_session)
    assert exc_zero_base.value.status_code == 400
    assert "Insufficient historical data" in exc_zero_base.value.detail


def test_layer_3_anomaly_severity_classifications(db_session, client):
    """REQ-006: Classifies deviation into all 5 severity levels using config thresholds."""
    from datetime import timedelta
    from app.anomaly import detect_ed_anomalies

    # Historical Thursday 14:00 rows (mean baseline = 40.0)
    t_hist1 = datetime(2026, 10, 15, 14, 0, 0, tzinfo=timezone.utc)
    t_hist2 = datetime(2026, 10, 22, 14, 0, 0, tzinfo=timezone.utc)
    t_current = datetime(2026, 10, 29, 14, 0, 0, tzinfo=timezone.utc)

    db_session.add(
        OperationalMetrics(
            timestamp=t_hist1,
            ed_arrivals=40,
            ed_patients=30,
            available_beds=40,
            icu_occupancy_pct=80.0,
            nurses_available=10,
            doctors_available=4,
        )
    )
    db_session.add(
        OperationalMetrics(
            timestamp=t_hist2,
            ed_arrivals=40,
            ed_patients=30,
            available_beds=40,
            icu_occupancy_pct=80.0,
            nurses_available=10,
            doctors_available=4,
        )
    )

    current_record = OperationalMetrics(
        timestamp=t_current,
        ed_arrivals=40,
        ed_patients=30,
        available_beds=40,
        icu_occupancy_pct=80.0,
        nurses_available=10,
        doctors_available=4,
    )
    db_session.add(current_record)
    db_session.commit()

    # Case 1: CRITICAL_SURGE (>= +30%) -> observed = 57 (deviation = +42.5%)
    current_record.ed_arrivals = 57
    db_session.commit()
    res = detect_ed_anomalies(db_session)
    assert res.severity == "CRITICAL_SURGE"
    assert res.is_anomaly is True
    assert res.deviation_pct == 42.5
    assert res.expected_baseline == 40.0
    assert "above" in res.explanation
    assert "Thursday 14:00" in res.explanation

    # Case 2: MODERATE_SURGE (+15% <= dev < +30%) -> observed = 48 (deviation = +20.0%)
    current_record.ed_arrivals = 48
    db_session.commit()
    res = detect_ed_anomalies(db_session)
    assert res.severity == "MODERATE_SURGE"
    assert res.is_anomaly is True
    assert res.deviation_pct == 20.0

    # Case 3: NORMAL (-15% < dev < +15%) -> observed = 41 (deviation = +2.5%)
    current_record.ed_arrivals = 41
    db_session.commit()
    res = detect_ed_anomalies(db_session)
    assert res.severity == "NORMAL"
    assert res.is_anomaly is False
    assert res.deviation_pct == 2.5

    # Case 4: MODERATE_DROP (-30% < dev <= -15%) -> observed = 32 (deviation = -20.0%)
    current_record.ed_arrivals = 32
    db_session.commit()
    res = detect_ed_anomalies(db_session)
    assert res.severity == "MODERATE_DROP"
    assert res.is_anomaly is True
    assert res.deviation_pct == -20.0
    assert "below" in res.explanation

    # Case 5: UNUSUAL_DROP (dev <= -30%) -> observed = 25 (deviation = -37.5%)
    current_record.ed_arrivals = 25
    db_session.commit()
    res = detect_ed_anomalies(db_session)
    assert res.severity == "UNUSUAL_DROP"
    assert res.is_anomaly is True
    assert res.deviation_pct == -37.5

    # API endpoint check via client
    response = client.get("/api/v1/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert data["timestamp"].endswith("Z")
    assert data["severity"] == "UNUSUAL_DROP"
    assert data["is_anomaly"] is True

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
    # Verify recent_arrivals: exactly 24 observed hourly values, oldest first
    assert len(forecast.recent_arrivals) == 24
    assert forecast.recent_arrivals[0].timestamp < forecast.recent_arrivals[-1].timestamp
    assert forecast.recent_arrivals[-1].arrivals == forecast.current_ed_arrivals

    # API endpoint call via client
    response = client.get("/api/v1/forecast")
    assert response.status_code == 200
    data = response.json()
    assert data["target_timestamp"].endswith("Z")
    assert data["current_ed_arrivals"] == 20 + 25
    assert data["predicted_ed_arrivals"] == forecast.predicted_ed_arrivals
    assert data["expected_net_change"] == forecast.expected_net_change
    assert len(data["recent_arrivals"]) == 24
    assert data["recent_arrivals"][0]["timestamp"].endswith("Z")


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


def test_layer_4_surge_scenario_recommends_nurses_and_disclaimer(db_session, client):
    """REQ-007: Surge scenario generates REC-001 nurse recommendation and includes advisory disclaimer."""
    from datetime import timedelta
    from app.optimizer import get_resource_recommendations
    from app.config import ADVISORY_DISCLAIMER

    base_time = datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc)
    # Insert 26 rows to allow Layer 2 forecasting
    for i in range(25):
        db_session.add(
            OperationalMetrics(
                timestamp=base_time + timedelta(hours=i),
                ed_arrivals=50,
                ed_patients=40,
                available_beds=60,
                icu_occupancy_pct=75.0,
                nurses_available=10,
                doctors_available=4,
            )
        )
    # Latest record at t=25: active=46, arrivals=57, nurses=10, doctors=4, beds=60, icu=75%
    latest_rec = OperationalMetrics(
        timestamp=base_time + timedelta(hours=25),
        ed_arrivals=57,
        ed_patients=46,
        available_beds=60,
        icu_occupancy_pct=75.0,
        nurses_available=10,
        doctors_available=4,
    )
    db_session.add(latest_rec)
    db_session.commit()

    # Function call
    result = get_resource_recommendations(db_session)

    # 1. Advisory disclaimer must be present in every response
    assert result.advisory_disclaimer == ADVISORY_DISCLAIMER
    assert "PROVISIONAL" in result.advisory_disclaimer

    # 2. Staffing recommendation
    rec_001 = next((r for r in result.recommendations if r.id == "REC-001"), None)
    assert rec_001 is not None
    assert rec_001.category == "STAFFING_NURSE"
    assert rec_001.priority == "HIGH"
    assert "additional nurse" in rec_001.action
    assert "Projected active load" in rec_001.rationale
    assert "Within max redeployment budget" in rec_001.constraints_checked

    # 3. No bed recommendation since beds=60 (>= 50) and icu=75.0% (< 88.0%)
    rec_002 = next((r for r in result.recommendations if r.id == "REC-002"), None)
    assert rec_002 is None

    # Endpoint test via client
    api_resp = client.get("/api/v1/recommendations")
    assert api_resp.status_code == 200
    data = api_resp.json()
    assert data["timestamp"].endswith("Z")
    assert data["advisory_disclaimer"] == ADVISORY_DISCLAIMER
    assert len(data["recommendations"]) >= 1


def test_layer_4_nurse_recommendation_capped_at_max(db_session):
    """REQ-007: Recommended nurses never exceeds MAX_NURSES_REDEPLOYABLE."""
    from datetime import timedelta
    from app.optimizer import get_resource_recommendations
    from app.config import MAX_NURSES_REDEPLOYABLE

    base_time = datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(25):
        db_session.add(
            OperationalMetrics(
                timestamp=base_time + timedelta(hours=i),
                ed_arrivals=50,
                ed_patients=40,
                available_beds=60,
                icu_occupancy_pct=75.0,
                nurses_available=5,
                doctors_available=2,
            )
        )
    # Huge active patient count (e.g. 120 patients with only 4 nurses) -> deficit > 20
    db_session.add(
        OperationalMetrics(
            timestamp=base_time + timedelta(hours=25),
            ed_arrivals=50,
            ed_patients=120,
            available_beds=60,
            icu_occupancy_pct=75.0,
            nurses_available=4,
            doctors_available=2,
        )
    )
    db_session.commit()

    result = get_resource_recommendations(db_session)
    rec_001 = next((r for r in result.recommendations if r.id == "REC-001"), None)
    assert rec_001 is not None
    # Must be capped at MAX_NURSES_REDEPLOYABLE (4)
    assert f"Consider allocating {MAX_NURSES_REDEPLOYABLE} additional nurses" in rec_001.action
    assert result.resource_state.nurse_deficit > MAX_NURSES_REDEPLOYABLE


def test_layer_4_bed_and_icu_rules_fire_separately_and_together(db_session):
    """REQ-007: Bed and ICU alert conditions fire separately and together, naming ONLY conditions that fired."""
    from datetime import timedelta
    from app.optimizer import get_resource_recommendations
    from app.config import MIN_AVAILABLE_BEDS_THRESHOLD, ICU_OCCUPANCY_WARNING_PCT

    base_time = datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(25):
        db_session.add(
            OperationalMetrics(
                timestamp=base_time + timedelta(hours=i),
                ed_arrivals=30,
                ed_patients=20,
                available_beds=60,
                icu_occupancy_pct=75.0,
                nurses_available=10,
                doctors_available=4,
            )
        )

    # 1. Only Bed alert fires (beds=42 < 50, icu=75.0% < 88.0%)
    latest_rec = OperationalMetrics(
        timestamp=base_time + timedelta(hours=25),
        ed_arrivals=30,
        ed_patients=20,
        available_beds=42,
        icu_occupancy_pct=75.0,
        nurses_available=10,
        doctors_available=4,
    )
    db_session.add(latest_rec)
    db_session.commit()

    res_bed_only = get_resource_recommendations(db_session)
    rec_bed = next((r for r in res_bed_only.recommendations if r.id == "REC-002"), None)
    assert rec_bed is not None
    assert f"Available beds (42) below minimum threshold ({MIN_AVAILABLE_BEDS_THRESHOLD})." == rec_bed.rationale
    assert "ICU occupancy" not in rec_bed.rationale

    # 2. Only ICU alert fires (beds=65 >= 50, icu=91.5% >= 88.0%)
    latest_rec.available_beds = 65
    latest_rec.icu_occupancy_pct = 91.5
    db_session.commit()

    res_icu_only = get_resource_recommendations(db_session)
    rec_icu = next((r for r in res_icu_only.recommendations if r.id == "REC-002"), None)
    assert rec_icu is not None
    assert f"ICU occupancy (91.5%) at or above warning level ({ICU_OCCUPANCY_WARNING_PCT:.1f}%)." == rec_icu.rationale
    assert "Available beds" not in rec_icu.rationale

    # 3. Both Bed and ICU alerts fire (beds=38 < 50, icu=92.0% >= 88.0%)
    latest_rec.available_beds = 38
    latest_rec.icu_occupancy_pct = 92.0
    db_session.commit()

    res_both = get_resource_recommendations(db_session)
    rec_both = next((r for r in res_both.recommendations if r.id == "REC-002"), None)
    assert rec_both is not None
    expected_rationale = (
        f"Available beds (38) below minimum threshold ({MIN_AVAILABLE_BEDS_THRESHOLD}) and "
        f"ICU occupancy (92.0%) at or above warning level ({ICU_OCCUPANCY_WARNING_PCT:.1f}%)."
    )
    assert rec_both.rationale == expected_rationale

    # 4. Neither alert fires (beds=60 >= 50, icu=80.0% < 88.0%)
    latest_rec.available_beds = 60
    latest_rec.icu_occupancy_pct = 80.0
    db_session.commit()

    res_neither = get_resource_recommendations(db_session)
    rec_neither = next((r for r in res_neither.recommendations if r.id == "REC-002"), None)
    assert rec_neither is None


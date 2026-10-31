import io
import pytest
from app.config import ADVISORY_DISCLAIMER


def test_e2e_all_five_endpoints_workflow(client):
    """End-to-end verification of all 5 API endpoints in sequence."""
    # 1. Ingest operational CSV with 26 hourly rows (enough for 24h lags + baseline)
    csv_rows = [
        "timestamp,ed_arrivals,ed_patients,available_beds,icu_occupancy_pct,nurses_available,doctors_available"
    ]
    for day in range(1, 28):
        # 27 rows: 2026-10-01 to 2026-10-27, same hour 14:00 to have matching day_of_week / hour_of_day
        pass

    # Build continuous 30-hour block with duplicate hour-of-week for anomaly detection
    # Using 14 days (336 hours) of synthetic hourly data from generate_synthetic_data
    from scripts.generate_synthetic_data import generate_synthetic_data
    df = generate_synthetic_data(days=14, seed=42)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")

    # Endpoint 1: POST /api/v1/ingest/csv
    r_ingest = client.post(
        "/api/v1/ingest/csv",
        files={"file": ("operations.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert r_ingest.status_code == 200
    ingest_data = r_ingest.json()
    assert ingest_data["status"] == "success"
    assert ingest_data["rows_processed"] == 14 * 24
    assert ingest_data["latest_timestamp"].endswith("Z")

    # Endpoint 2: GET /api/v1/current-state
    r_state = client.get("/api/v1/current-state")
    assert r_state.status_code == 200
    state_data = r_state.json()
    assert state_data["timestamp"].endswith("Z")
    assert "metrics" in state_data
    assert "patient_to_nurse_ratio" in state_data["metrics"]
    assert "patient_to_doctor_ratio" in state_data["metrics"]

    # Endpoint 3: GET /api/v1/forecast
    r_forecast = client.get("/api/v1/forecast")
    assert r_forecast.status_code == 200
    forecast_data = r_forecast.json()
    assert forecast_data["target_timestamp"].endswith("Z")
    assert forecast_data["predicted_ed_arrivals"] >= 0
    assert "model_metadata" in forecast_data

    # Endpoint 4: GET /api/v1/anomalies
    r_anom = client.get("/api/v1/anomalies")
    assert r_anom.status_code == 200
    anom_data = r_anom.json()
    assert anom_data["timestamp"].endswith("Z")
    assert anom_data["severity"] in [
        "NORMAL",
        "MODERATE_SURGE",
        "CRITICAL_SURGE",
        "MODERATE_DROP",
        "UNUSUAL_DROP",
    ]
    assert isinstance(anom_data["is_anomaly"], bool)
    assert "explanation" in anom_data

    # Endpoint 5: GET /api/v1/recommendations
    r_rec = client.get("/api/v1/recommendations")
    assert r_rec.status_code == 200
    rec_data = r_rec.json()
    assert rec_data["timestamp"].endswith("Z")
    assert rec_data["advisory_disclaimer"] == ADVISORY_DISCLAIMER
    assert "resource_state" in rec_data
    assert isinstance(rec_data["recommendations"], list)

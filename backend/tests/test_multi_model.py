from datetime import datetime, timedelta, timezone
import pytest
from app.database import OperationalMetrics


@pytest.fixture
def populated_db_for_forecasting(db_session):
    """Inserts 26 hours of continuous operational data for testing multi-model forecast inference."""
    base_time = datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(26):
        db_session.add(
            OperationalMetrics(
                timestamp=base_time + timedelta(hours=i),
                ed_arrivals=25 + (i % 10),
                ed_patients=20 + i,
                available_beds=55,
                icu_occupancy_pct=72.0,
                nurses_available=10,
                doctors_available=4,
            )
        )
    db_session.commit()
    return db_session


def test_get_models_benchmark_leaderboard(client):
    """GET /api/v1/forecast/models returns comparative evaluation metrics for all paradigms."""
    res = client.get("/api/v1/forecast/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert len(data["models"]) >= 4

    model_ids = [m["id"] for m in data["models"]]
    assert "hist_gbr" in model_ids
    assert "lstm" in model_ids
    assert "holt_winters" in model_ids
    assert "seasonal_naive" in model_ids

    # Check metrics existence
    for m in data["models"]:
        assert m["mae"] > 0
        assert m["rmse"] > 0
        assert m["latency_ms"] >= 0


def test_forecast_with_each_model_paradigm(client, populated_db_for_forecasting):
    """Verify that /forecast route can execute each model paradigm cleanly."""
    # 1. Default (HistGBR)
    res_default = client.get("/api/v1/forecast")
    assert res_default.status_code == 200
    d_default = res_default.json()
    assert d_default["model_metadata"]["model_id"] == "hist_gbr"
    assert d_default["predicted_ed_arrivals"] >= 0

    # 2. PyTorch LSTM
    res_lstm = client.get("/api/v1/forecast?model=lstm")
    assert res_lstm.status_code == 200
    d_lstm = res_lstm.json()
    assert d_lstm["model_metadata"]["model_name"] == "PyTorch LSTM"
    assert d_lstm["model_metadata"]["paradigm"] == "Recurrent Neural Network"
    assert d_lstm["predicted_ed_arrivals"] >= 0

    # 3. Holt-Winters
    res_hw = client.get("/api/v1/forecast?model=holt_winters")
    assert res_hw.status_code == 200
    d_hw = res_hw.json()
    assert d_hw["model_metadata"]["model_name"] == "Holt-Winters (HW-ETS)"
    assert d_hw["model_metadata"]["paradigm"] == "Statistical Additive Time Series"
    assert d_hw["predicted_ed_arrivals"] >= 0

    # 4. Seasonal Naive
    res_naive = client.get("/api/v1/forecast?model=seasonal_naive")
    assert res_naive.status_code == 200
    d_naive = res_naive.json()
    assert d_naive["model_metadata"]["model_name"] == "Seasonal Naive (Lag-24)"
    assert d_naive["predicted_ed_arrivals"] >= 0

    # 5. Invalid model returns HTTP 400
    res_invalid = client.get("/api/v1/forecast?model=unknown_transformer")
    assert res_invalid.status_code == 400
    assert "Unknown forecasting model" in res_invalid.json()["detail"]


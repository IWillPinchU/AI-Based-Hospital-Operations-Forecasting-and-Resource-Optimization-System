import os
import joblib
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

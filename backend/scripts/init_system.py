"""System bootstrap script for Docker and automated environments.

Ensures:
1. Baseline operational dataset (hospital_operations_synthetic.csv) exists.
2. Forecasting models and benchmark artifacts are trained if missing.
3. Database is initialized and pre-seeded with initial telemetry rows.
"""

import os
import sys
from pathlib import Path

# Set up paths intelligently for both local repo and Docker container execution
SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parent  # e.g., /app or repo/backend
if (APP_DIR.parent / "backend").exists() and (APP_DIR.parent / "frontend").exists():
    ROOT_DIR = APP_DIR.parent
else:
    ROOT_DIR = APP_DIR

sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
from app.database import init_db, SessionLocal, OperationalMetrics
from app.ingestion import parse_and_validate_csv
from app.anomaly import scan_and_record_all_anomalies


def bootstrap():
    print("🏥 [Bootstrap] Checking hospital system prerequisites...")

    csv_path = ROOT_DIR / "hospital_operations_synthetic.csv"
    surge_csv_path = ROOT_DIR / "surge_demo.csv"
    models_dir = APP_DIR / "models"
    benchmark_json = models_dir / "model_benchmark.json"

    # 1. Generate synthetic dataset if not present
    if not csv_path.exists() or not surge_csv_path.exists():
        print("📊 [Bootstrap] Generating realistic hospital operational datasets...")
        from scripts.generate_synthetic_data import generate_synthetic_data, generate_surge_demo_data

        df_synthetic = generate_synthetic_data(days=30, seed=42)
        df_synthetic.to_csv(csv_path, index=False)
        print(f"   ✓ Created {csv_path.name} ({len(df_synthetic)} rows)")

        df_surge = generate_surge_demo_data(days=14, seed=42)
        df_surge.to_csv(surge_csv_path, index=False)
        print(f"   ✓ Created {surge_csv_path.name} ({len(df_surge)} rows)")
    else:
        print("✓ Datasets already exist.")

    # 2. Train models if benchmark is missing
    if not benchmark_json.exists():
        print("🧠 [Bootstrap] Training multi-model forecasting zoo (HistGBR, LSTM, Holt-Winters)...")
        from scripts.train_all_models import main as train_models

        # Override sys.argv to point to explicit data and model paths
        saved_argv = sys.argv
        try:
            sys.argv = [
                "train_all_models.py",
                "--data",
                str(csv_path),
                "--models-dir",
                str(models_dir),
            ]
            train_models()
        finally:
            sys.argv = saved_argv
        print("   ✓ Multi-model training complete.")
    else:
        print("✓ Model artifacts already trained and cached.")

    # 3. Seed SQLite Database
    init_db()
    db = SessionLocal()
    try:
        row_count = db.query(OperationalMetrics).count()
        if row_count == 0 and csv_path.exists():
            print("💾 [Bootstrap] Pre-seeding SQLite database with baseline operational records...")
            with open(csv_path, "rb") as f:
                content = f.read()
            df = parse_and_validate_csv(content)
            for _, row in df.iterrows():
                db.add(
                    OperationalMetrics(
                        timestamp=row["timestamp"].to_pydatetime().replace(tzinfo=None),
                        ed_arrivals=int(row["ed_arrivals"]),
                        ed_patients=int(row["ed_patients"]),
                        available_beds=int(row["available_beds"]),
                        icu_occupancy_pct=float(row["icu_occupancy_pct"]),
                        nurses_available=int(row["nurses_available"]),
                        doctors_available=int(row["doctors_available"]),
                    )
                )
            db.commit()
            print(f"   ✓ Ingested {len(df)} initial telemetry records.")

            # Scan and catalog historical anomalies
            new_anomalies = scan_and_record_all_anomalies(db)
            print(f"   ✓ Indexed {new_anomalies} historical surge events into anomaly audit log.")
        else:
            print(f"✓ Database already contains {row_count} operational telemetry rows.")
    finally:
        db.close()

    print("🚀 [Bootstrap] System ready for operational traffic.\n")


if __name__ == "__main__":
    bootstrap()

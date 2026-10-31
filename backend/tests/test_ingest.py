import io
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.database import get_db, Base, OperationalMetrics




def test_empty_database_returns_404(client):
    """GET /current-state returns 404 when no data has been uploaded."""
    response = client.get("/api/v1/current-state")
    assert response.status_code == 404
    assert "No operational data available" in response.json()["detail"]


def test_csv_ingest_success_and_malformed(client):
    """REQ-001: Valid CSV uploads successfully; non-CSV and malformed files return 422."""
    valid_csv = (
        "timestamp,ed_arrivals,ed_patients,available_beds,icu_occupancy_pct,nurses_available,doctors_available\n"
        "2026-10-29T13:00:00Z,50,40,45,85.0,10,4\n"
        "2026-10-29T14:00:00Z,57,46,42,87.0,10,4\n"
    )

    # 1. Valid upload
    file = io.BytesIO(valid_csv.encode("utf-8"))
    response = client.post(
        "/api/v1/ingest/csv",
        files={"file": ("test_valid.csv", file, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["rows_processed"] == 2
    assert data["rows_inserted"] == 2
    assert data["rows_updated"] == 0

    # 2. Non-CSV file rejection
    txt_file = io.BytesIO(b"hello world")
    response_txt = client.post(
        "/api/v1/ingest/csv",
        files={"file": ("test.txt", txt_file, "text/plain")},
    )
    assert response_txt.status_code == 422

    # 3. Missing required columns
    bad_cols_csv = (
        "timestamp,ed_arrivals\n"
        "2026-10-29T13:00:00Z,50\n"
    )
    bad_file = io.BytesIO(bad_cols_csv.encode("utf-8"))
    response_bad = client.post(
        "/api/v1/ingest/csv",
        files={"file": ("bad_cols.csv", bad_file, "text/csv")},
    )
    assert response_bad.status_code == 422
    assert "missing required columns" in response_bad.json()["detail"].lower()


def test_schema_validation_ranges(client):
    """REQ-002: Rejects negative counts and out-of-range ICU percentages."""
    # Negative arrivals
    neg_csv = (
        "timestamp,ed_arrivals,ed_patients,available_beds,icu_occupancy_pct,nurses_available,doctors_available\n"
        "2026-10-29T13:00:00Z,-5,40,45,85.0,10,4\n"
    )
    response_neg = client.post(
        "/api/v1/ingest/csv",
        files={"file": ("neg.csv", io.BytesIO(neg_csv.encode("utf-8")), "text/csv")},
    )
    assert response_neg.status_code == 422

    # ICU occupancy > 100%
    icu_csv = (
        "timestamp,ed_arrivals,ed_patients,available_beds,icu_occupancy_pct,nurses_available,doctors_available\n"
        "2026-10-29T13:00:00Z,50,40,45,108.5,10,4\n"
    )
    response_icu = client.post(
        "/api/v1/ingest/csv",
        files={"file": ("icu.csv", io.BytesIO(icu_csv.encode("utf-8")), "text/csv")},
    )
    assert response_icu.status_code == 422


def test_reuploading_same_csv_is_idempotent(client):
    """Demo resilience: Re-uploading the same CSV updates existing rows without crashing or duplicating."""
    csv_content = (
        "timestamp,ed_arrivals,ed_patients,available_beds,icu_occupancy_pct,nurses_available,doctors_available\n"
        "2026-10-29T10:00:00Z,30,25,60,78.0,8,3\n"
        "2026-10-29T11:00:00Z,35,28,58,80.0,8,3\n"
    )

    # First upload -> 2 inserted
    response1 = client.post(
        "/api/v1/ingest/csv",
        files={"file": ("demo.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response1.status_code == 200
    assert response1.json()["rows_inserted"] == 2
    assert response1.json()["rows_updated"] == 0

    # Second upload of identical file -> 2 updated, 0 inserted, NO crash
    response2 = client.post(
        "/api/v1/ingest/csv",
        files={"file": ("demo.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response2.status_code == 200
    assert response2.json()["rows_inserted"] == 0
    assert response2.json()["rows_updated"] == 2


def test_layer_1_current_state_metrics(client):
    """REQ-004: GET /current-state returns the latest chronological record with derived load ratios."""
    csv_content = (
        "timestamp,ed_arrivals,ed_patients,available_beds,icu_occupancy_pct,nurses_available,doctors_available\n"
        "2026-10-29T13:00:00Z,50,40,45,85.0,10,4\n"
        "2026-10-29T14:00:00Z,57,46,42,87.0,10,4\n"
    )
    client.post(
        "/api/v1/ingest/csv",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )

    response = client.get("/api/v1/current-state")
    assert response.status_code == 200
    data = response.json()

    # Matches the latest record (14:00) with UTC trailing 'Z'
    assert data["timestamp"] == "2026-10-29T14:00:00Z"
    assert data["timestamp"].endswith("Z")
    assert data["ed_arrivals"] == 57
    assert data["ed_patients"] == 46
    assert data["available_beds"] == 42
    assert data["icu_occupancy_pct"] == 87.0
    assert data["nurses_available"] == 10
    assert data["doctors_available"] == 4

    # Ratios calculated accurately
    # 46 patients / 10 nurses = 4.6
    # 46 patients / 4 doctors = 11.5
    assert data["metrics"]["patient_to_nurse_ratio"] == 4.6
    assert data["metrics"]["patient_to_doctor_ratio"] == 11.5

import io
from datetime import datetime, timezone, timedelta
import pytest
from app.database import OperationalMetrics, AnomalyEvent
import openpyxl


def seed_records(db_session, count: int = 24):
    start_ts = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(count):
        ts = start_ts + timedelta(hours=i)
        db_session.add(
            OperationalMetrics(
                timestamp=ts,
                ed_arrivals=25 + (i % 10),
                ed_patients=20 + (i % 8),
                available_beds=50 - (i % 5),
                icu_occupancy_pct=75.0 + (i % 10),
                nurses_available=10,
                doctors_available=4,
            )
        )
    # Add an anomaly event
    db_session.add(
        AnomalyEvent(
            timestamp=start_ts + timedelta(hours=5),
            observed_value=48,
            expected_baseline=30.0,
            deviation_pct=60.0,
            severity="CRITICAL_SURGE",
            explanation="Critical surge in arrivals",
            resolved=False,
        )
    )
    db_session.commit()


def test_shift_report_empty_database_returns_404(client):
    res = client.get("/api/v1/reports/shift?hours=12&format=pdf")
    assert res.status_code == 404
    assert "No operational records available" in res.json()["detail"]


def test_shift_report_pdf_generation_success(client, db_session):
    seed_records(db_session, 24)
    res = client.get("/api/v1/reports/shift?hours=12&format=pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=\"hospital_shift_report_12h_" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")


def test_shift_report_excel_generation_success(client, db_session):
    seed_records(db_session, 24)
    res = client.get("/api/v1/reports/shift?hours=12&format=excel")
    assert res.status_code == 200
    assert "spreadsheetml.sheet" in res.headers["content-type"]
    assert "attachment; filename=\"hospital_shift_report_12h_" in res.headers["content-disposition"]
    # Excel is a zip file, starts with PK\x03\x04
    assert res.content.startswith(b"PK\x03\x04")

    # Read the workbook in memory and verify worksheet structure
    wb = openpyxl.load_workbook(io.BytesIO(res.content))
    assert "Shift Summary" in wb.sheetnames
    assert "Hourly Telemetry" in wb.sheetnames
    assert "Anomaly Incident Log" in wb.sheetnames


def test_shift_report_custom_durations(client, db_session):
    seed_records(db_session, 30)
    for hours in [8, 12, 24]:
        res = client.get(f"/api/v1/reports/shift?hours={hours}&format=pdf")
        assert res.status_code == 200
        assert f"hospital_shift_report_{hours}h_" in res.headers["content-disposition"]


def test_shift_report_invalid_format_returns_400(client, db_session):
    seed_records(db_session, 10)
    res = client.get("/api/v1/reports/shift?hours=12&format=unsupported_format")
    assert res.status_code == 400
    assert "Invalid format" in res.json()["detail"]

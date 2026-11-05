from datetime import datetime, timezone, timedelta
from app.database import OperationalMetrics


def test_history_empty_database(client):
    """Empty database returns 200 with empty records list and None summary."""
    response = client.get("/api/v1/history")
    assert response.status_code == 200
    data = response.json()
    assert data["records"] == []
    assert data["summary"] is None


def test_history_with_records_and_aggregates(client, db_session):
    """Populated database returns chronological records and statistical summary."""
    base_time = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(48):
        db_session.add(
            OperationalMetrics(
                timestamp=base_time + timedelta(hours=i),
                ed_arrivals=20 + i,
                ed_patients=15 + (i % 5),
                available_beds=50 - (i % 10),
                icu_occupancy_pct=60.0 + (i % 20),
                nurses_available=10,
                doctors_available=4,
            )
        )
    db_session.commit()

    response = client.get("/api/v1/history")
    assert response.status_code == 200
    data = response.json()

    assert len(data["records"]) == 48
    # Records should be chronological ascending
    assert data["records"][0]["ed_arrivals"] == 20
    assert data["records"][-1]["ed_arrivals"] == 20 + 47

    summary = data["summary"]
    assert summary is not None
    assert summary["total_records"] == 48
    assert summary["peak_arrivals"] == 67
    assert summary["ed_arrivals"]["min"] == 20.0
    assert summary["ed_arrivals"]["max"] == 67.0
    assert summary["ed_arrivals"]["total"] == sum(20 + i for i in range(48))


def test_history_date_filtering(client, db_session):
    """Filters historical telemetry by start and end timestamps."""
    base_time = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(50):
        db_session.add(
            OperationalMetrics(
                timestamp=base_time + timedelta(hours=i),
                ed_arrivals=10 + i,
                ed_patients=20,
                available_beds=40,
                icu_occupancy_pct=75.0,
                nurses_available=8,
                doctors_available=3,
            )
        )
    db_session.commit()

    start_iso = (base_time + timedelta(hours=10)).isoformat()
    end_iso = (base_time + timedelta(hours=20)).isoformat()

    response = client.get(f"/api/v1/history?start={start_iso}&end={end_iso}")
    assert response.status_code == 200
    data = response.json()

    assert len(data["records"]) == 11
    assert data["records"][0]["ed_arrivals"] == 20  # hour 10: 10 + 10
    assert data["records"][-1]["ed_arrivals"] == 30  # hour 20: 10 + 20
    assert data["summary"]["total_records"] == 11


def test_history_limit_parameter(client, db_session):
    """Limit parameter restricts max rows returned."""
    base_time = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(30):
        db_session.add(
            OperationalMetrics(
                timestamp=base_time + timedelta(hours=i),
                ed_arrivals=15,
                ed_patients=20,
                available_beds=45,
                icu_occupancy_pct=70.0,
                nurses_available=8,
                doctors_available=3,
            )
        )
    db_session.commit()

    response = client.get("/api/v1/history?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["records"]) == 5


def test_history_invalid_datetime_format(client):
    """Malformed datetime string in start/end query returns HTTP 400."""
    response = client.get("/api/v1/history?start=not-a-date")
    assert response.status_code == 400
    assert "Invalid datetime format" in response.json()["detail"]

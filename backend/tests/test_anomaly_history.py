from datetime import datetime, timezone, timedelta
from app.database import OperationalMetrics, AnomalyEvent
from app.anomaly import detect_ed_anomalies, scan_and_record_all_anomalies


def test_anomaly_history_empty_table(client):
    """Empty database returns 0 events and empty summary."""
    response = client.get("/api/v1/anomalies/history")
    assert response.status_code == 200
    data = response.json()
    assert data["events"] == []
    assert data["summary"]["total_anomalies"] == 0
    assert data["summary"]["unresolved_count"] == 0


def test_detect_ed_anomalies_auto_persists_event(client, db_session):
    """When detect_ed_anomalies identifies a surge, it auto-persists to anomaly_events table."""
    base_time = datetime(2026, 10, 1, 14, 0, 0, tzinfo=timezone.utc)
    # Add historical baseline rows: Thursdays at 14:00 (arrivals = 20)
    for week in range(4):
        db_session.add(
            OperationalMetrics(
                timestamp=base_time + timedelta(days=week * 7),
                ed_arrivals=20,
                ed_patients=15,
                available_beds=50,
                icu_occupancy_pct=60.0,
                nurses_available=10,
                doctors_available=4,
            )
        )
    # Latest record: massive surge (arrivals = 60, +200% surge)
    latest_time = base_time + timedelta(days=28)
    db_session.add(
        OperationalMetrics(
            timestamp=latest_time,
            ed_arrivals=60,
            ed_patients=35,
            available_beds=40,
            icu_occupancy_pct=75.0,
            nurses_available=10,
            doctors_available=4,
        )
    )
    db_session.commit()

    # Call Layer 3 anomaly detection
    res = client.get("/api/v1/anomalies")
    assert res.status_code == 200
    assert res.json()["is_anomaly"] is True
    assert res.json()["severity"] == "CRITICAL_SURGE"

    # Verify event is in anomaly_events
    history_res = client.get("/api/v1/anomalies/history")
    assert history_res.status_code == 200
    data = history_res.json()
    assert len(data["events"]) == 1
    event = data["events"][0]
    assert event["severity"] == "CRITICAL_SURGE"
    assert event["observed_value"] == 60
    assert event["expected_baseline"] == 20.0
    assert event["deviation_pct"] == 200.0
    assert event["resolved"] is False

    summary = data["summary"]
    assert summary["total_anomalies"] == 1
    assert summary["critical_surges"] == 1
    assert summary["unresolved_count"] == 1


def test_resolve_and_unresolve_anomaly_event(client, db_session):
    """Can resolve and reopen an anomaly event via API."""
    event_time = datetime(2026, 10, 15, 10, 0, 0, tzinfo=timezone.utc)
    event = AnomalyEvent(
        timestamp=event_time,
        observed_value=50,
        expected_baseline=25.0,
        deviation_pct=100.0,
        severity="CRITICAL_SURGE",
        explanation="Surge detected",
        resolved=False,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    # Resolve event
    res = client.post(f"/api/v1/anomalies/{event.id}/resolve?resolved=true")
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["resolved"] is True
    assert res_data["resolved_at"] is not None
    assert res_data["status"] == "resolved"

    # Verify in history
    history_res = client.get("/api/v1/anomalies/history?resolved=true")
    assert history_res.status_code == 200
    assert len(history_res.json()["events"]) == 1
    assert history_res.json()["summary"]["resolved_count"] == 1

    # Unresolve event
    unres = client.post(f"/api/v1/anomalies/{event.id}/resolve?resolved=false")
    assert unres.status_code == 200
    assert unres.json()["resolved"] is False
    assert unres.json()["status"] == "unresolved"


def test_resolve_non_existent_event_returns_404(client):
    """Attempting to resolve unknown event ID returns HTTP 404."""
    res = client.post("/api/v1/anomalies/99999/resolve")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_scan_and_record_historical_anomalies(client, db_session):
    """Scan endpoint analyzes historical data and persists detected anomalies."""
    base_time = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    # Generate 14 days of data: Day 12 hour 15 has a surge
    for day in range(14):
        for h in range(24):
            arrivals = 20
            if day == 12 and h == 15:
                arrivals = 65  # Huge surge
            db_session.add(
                OperationalMetrics(
                    timestamp=base_time + timedelta(days=day, hours=h),
                    ed_arrivals=arrivals,
                    ed_patients=15,
                    available_beds=50,
                    icu_occupancy_pct=65.0,
                    nurses_available=10,
                    doctors_available=4,
                )
            )
    db_session.commit()

    scan_res = client.post("/api/v1/anomalies/scan")
    assert scan_res.status_code == 200
    assert scan_res.json()["new_anomalies_recorded"] >= 1

    history_res = client.get("/api/v1/anomalies/history?severity=CRITICAL_SURGE")
    assert history_res.status_code == 200
    assert len(history_res.json()["events"]) >= 1


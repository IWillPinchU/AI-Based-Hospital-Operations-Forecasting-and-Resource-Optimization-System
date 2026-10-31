import io
from datetime import datetime, timezone

from app.schemas import OperationalRowSchema
from scripts.generate_synthetic_data import generate_synthetic_data
from scripts.simulate_live_feed import build_next_record, main


def _row(ts, arrivals):
    return {
        "timestamp": ts,
        "ed_arrivals": str(arrivals),
        "ed_patients": "40",
        "available_beds": "30",
        "icu_occupancy_pct": "80.5",
        "nurses_available": "10",
        "doctors_available": "4",
    }


def test_build_next_record_is_next_hour_same_hour_of_week():
    # 2026-10-01 is a Thursday; the new timestamp is Thursday 11:00.
    rows = [
        _row("2026-10-01T10:00:00+00:00", 11),  # wrong hour
        _row("2026-10-02T11:00:00+00:00", 22),  # Friday 11:00, wrong weekday
        _row("2026-10-08T11:00:00+00:00", 33),  # Thursday 11:00, match
    ]
    latest = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)
    rec = build_next_record(latest, rows)
    assert rec["timestamp"] == "2026-10-15T11:00:00Z"
    assert rec["ed_arrivals"] == 33
    assert rec["icu_occupancy_pct"] == 80.5


def test_build_next_record_passes_schema():
    rows = [_row("2026-10-08T11:00:00+00:00", 33)]
    rec = build_next_record(datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc), rows)
    OperationalRowSchema(**rec)


def test_simulated_record_posts_and_becomes_current(client):
    # 8 days covers every weekday, so the next hour always has a source match.
    df = generate_synthetic_data(days=8, seed=42)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    r = client.post(
        "/api/v1/ingest/csv",
        files={"file": ("ops.csv", io.BytesIO(buf.getvalue().encode("utf-8")), "text/csv")},
    )
    assert r.status_code == 200

    latest = datetime.fromisoformat(client.get("/api/v1/current-state").json()["timestamp"].replace("Z", "+00:00"))
    rec = build_next_record(latest, df.to_dict("records"))
    r = client.post("/api/v1/ingest/record", json=rec)
    assert r.status_code == 200
    assert r.json()["action"] == "inserted"

    state = client.get("/api/v1/current-state").json()
    assert state["timestamp"] == rec["timestamp"]
    assert state["ed_arrivals"] == rec["ed_arrivals"]
    assert state["icu_occupancy_pct"] == rec["icu_occupancy_pct"]


def test_simulator_exits_cleanly_when_backend_unreachable(capsys):
    code = main(["--api-base", "http://127.0.0.1:1", "--count", "1"])
    assert code == 1
    assert "Cannot reach the backend" in capsys.readouterr().err

from app.database import OperationalMetrics


def _rec(ts, **over):
    body = {
        "timestamp": ts,
        "ed_arrivals": 50,
        "ed_patients": 40,
        "available_beds": 30,
        "icu_occupancy_pct": 80.0,
        "nurses_available": 10,
        "doctors_available": 4,
    }
    body.update(over)
    return body


def _count(db_session):
    return db_session.query(OperationalMetrics).count()


def test_post_record_inserts_and_updates_current_state(client):
    r = client.post("/api/v1/ingest/record", json=_rec("2026-10-29T10:00:00Z"))
    assert r.status_code == 200
    assert r.json()["action"] == "inserted"
    state = client.get("/api/v1/current-state").json()
    assert state["timestamp"].startswith("2026-10-29T10:00:00")
    assert state["ed_arrivals"] == 50

    r = client.post(
        "/api/v1/ingest/record", json=_rec("2026-10-29T11:00:00Z", ed_arrivals=77)
    )
    assert r.status_code == 200
    state = client.get("/api/v1/current-state").json()
    assert state["timestamp"].startswith("2026-10-29T11:00:00")
    assert state["ed_arrivals"] == 77


def test_post_record_duplicate_timestamp_updates(client, db_session):
    ts = "2026-10-29T10:00:00Z"
    assert client.post("/api/v1/ingest/record", json=_rec(ts)).json()["action"] == "inserted"
    r = client.post(
        "/api/v1/ingest/record",
        json=_rec(ts, ed_arrivals=99, ed_patients=88, available_beds=7,
                  icu_occupancy_pct=55.5, nurses_available=3, doctors_available=2),
    )
    assert r.json()["action"] == "updated"
    db_session.expire_all()
    assert _count(db_session) == 1
    row = db_session.query(OperationalMetrics).one()
    assert (row.ed_arrivals, row.ed_patients, row.available_beds) == (99, 88, 7)
    assert (row.icu_occupancy_pct, row.nurses_available, row.doctors_available) == (55.5, 3, 2)


def test_post_record_rejects_invalid_and_missing_fields(client, db_session):
    ts = "2026-10-29T10:00:00Z"
    bad = [_rec(ts, ed_arrivals=-1), _rec(ts, icu_occupancy_pct=100.1)]
    missing = _rec(ts)
    del missing["doctors_available"]
    bad.append(missing)
    bad.append(_rec("not-a-timestamp"))
    for body in bad:
        assert client.post("/api/v1/ingest/record", json=body).status_code == 422
    assert _count(db_session) == 0


def test_post_record_out_of_order_does_not_change_current_state(client, db_session):
    client.post("/api/v1/ingest/record", json=_rec("2026-10-29T10:00:00Z", ed_arrivals=60))
    client.post("/api/v1/ingest/record", json=_rec("2026-10-29T08:00:00Z", ed_arrivals=20))
    state = client.get("/api/v1/current-state").json()
    assert state["timestamp"].startswith("2026-10-29T10:00:00")
    assert state["ed_arrivals"] == 60
    assert _count(db_session) == 2


def test_post_record_naive_timestamp_treated_as_utc(client):
    r = client.post("/api/v1/ingest/record", json=_rec("2026-10-29T14:00:00"))
    assert r.status_code == 200
    ts = r.json()["timestamp"]
    assert ts.endswith("Z")
    assert ts.startswith("2026-10-29T14:00:00")


def test_post_record_other_offset_matches_existing_row(client, db_session):
    client.post("/api/v1/ingest/record", json=_rec("2026-10-29T14:00:00Z"))
    r = client.post(
        "/api/v1/ingest/record",
        json=_rec("2026-10-29T19:30:00+05:30", ed_arrivals=91),
    )
    assert r.json()["action"] == "updated"
    db_session.expire_all()
    assert _count(db_session) == 1
    assert db_session.query(OperationalMetrics).one().ed_arrivals == 91

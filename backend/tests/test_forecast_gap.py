import io

from scripts.generate_synthetic_data import generate_synthetic_data

GAP_DETAIL = "Data has a gap in the last 25 hours; upload or send the missing hours"


def _upload(client, df):
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    r = client.post(
        "/api/v1/ingest/csv",
        files={"file": ("operations.csv", io.BytesIO(buf.getvalue().encode()), "text/csv")},
    )
    assert r.status_code == 200


def test_forecast_gap_returns_400(client):
    df = generate_synthetic_data(days=3, seed=42)
    df = df.drop(df.index[-10]).reset_index(drop=True)
    _upload(client, df)

    r = client.get("/api/v1/forecast")
    assert r.status_code == 400
    assert r.json()["detail"] == GAP_DETAIL
    assert client.get("/api/v1/recommendations").status_code == 400


def test_forecast_consecutive_hours_ok(client):
    _upload(client, generate_synthetic_data(days=3, seed=42))
    assert client.get("/api/v1/forecast").status_code == 200

import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_websocket_telemetry_connection_and_ping(client):
    """Verify WebSocket client connects, receives welcome event, and handles ping-pong."""
    with client.websocket_connect("/api/v1/ws/telemetry") as ws:
        msg = ws.receive_json()
        assert msg["event"] == "connected"
        assert "stream" in msg["message"].lower()

        # Ping-pong heartbeat test
        ws.send_text("ping")
        resp = ws.receive_text()
        assert resp == "pong"


def test_websocket_broadcast_on_record_ingest(client):
    """Verify that posting a record broadcasts a 'data_updated' event to connected WebSockets."""
    payload = {
        "timestamp": "2026-10-29T15:00:00Z",
        "ed_arrivals": 45,
        "ed_patients": 35,
        "available_beds": 50,
        "icu_occupancy_pct": 80.0,
        "nurses_available": 10,
        "doctors_available": 4,
    }

    with client.websocket_connect("/api/v1/ws/telemetry") as ws:
        # Drain the initial connection message
        init_msg = ws.receive_json()
        assert init_msg["event"] == "connected"

        # Ingest a live record via HTTP POST
        res = client.post("/api/v1/ingest/record", json=payload)
        assert res.status_code == 200

        # Verify broadcast received on WebSocket
        broadcast = ws.receive_json()
        assert broadcast["event"] == "data_updated"
        assert broadcast["source"] == "live_feed"
        assert broadcast["action"] in ["inserted", "updated"]


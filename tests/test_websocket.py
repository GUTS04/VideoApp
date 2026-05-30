"""WebSocket tests — requires PostgreSQL and migrations."""

import pytest
from fastapi.testclient import TestClient

from tests.helpers import register_user as _register_and_token


def test_websocket_connection_info(client: TestClient) -> None:
    response = client.get("/api/v1/ws/connection-info")
    assert response.status_code == 200
    body = response.json()
    assert "/ws/connect" in body["websocket_url"]
    assert "connection_flow" in body


def test_websocket_authenticated_connect_and_ping(client: TestClient) -> None:
    user, token = _register_and_token(client, label="ws")

    with client.websocket_connect(f"/ws/connect?token={token}") as ws:
        connected = ws.receive_json()
        assert connected["type"] == "connected"
        assert connected["user_id"] == user["id"]
        assert "online_users" in connected

        presence = ws.receive_json()
        assert presence["type"] == "presence"

        ws.send_text("ping")
        pong = ws.receive_json()
        assert pong["type"] == "pong"


def test_websocket_rejects_missing_token(client: TestClient) -> None:
    with pytest.raises(Exception):  # noqa: PT011 — TestClient raises on close
        with client.websocket_connect("/ws/connect") as ws:
            ws.receive_text()


def test_websocket_rejects_invalid_token(client: TestClient) -> None:
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/connect?token=not-a-valid-jwt") as ws:
            ws.receive_text()


def test_websocket_status_requires_http_auth(client: TestClient) -> None:
    response = client.get("/api/v1/ws/status")
    assert response.status_code == 403


def test_websocket_status_after_connect(client: TestClient) -> None:
    _, token = _register_and_token(client, label="ws_status")

    with client.websocket_connect(f"/ws/connect?token={token}") as ws:
        ws.receive_json()

        status = client.get(
            "/api/v1/ws/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status.status_code == 200
        body = status.json()
        assert body["active_connections"] >= 1
        assert body["unique_users_online"] >= 1

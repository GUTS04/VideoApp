"""Direct messaging WebSocket tests."""

import json
import uuid

from fastapi.testclient import TestClient

from tests.helpers import register_user as _register_user


def _recv_until_type(ws, expected_type: str, max_messages: int = 5) -> dict:
    for _ in range(max_messages):
        msg = ws.receive_json()
        if msg.get("type") == expected_type:
            return msg
    raise AssertionError(f"Did not receive {expected_type!r} within {max_messages} messages")


def test_direct_message_delivery(client: TestClient) -> None:
    user_a, token_a = _register_user(client, label="usera", gender="male")
    user_b, token_b = _register_user(client, label="userb", gender="female")

    with client.websocket_connect(f"/ws/connect?token={token_a}") as ws_a:
        _recv_until_type(ws_a, "connected")
        _recv_until_type(ws_a, "presence")

        with client.websocket_connect(f"/ws/connect?token={token_b}") as ws_b:
            _recv_until_type(ws_b, "connected")
            _recv_until_type(ws_b, "presence")
            connected_event = _recv_until_type(ws_a, "user_connected")
            assert connected_event["user_id"] == user_b["id"]

            ws_a.send_text(
                json.dumps(
                    {
                        "type": "chat_message",
                        "to_user_id": user_b["id"],
                        "content": "Hello from A",
                    }
                )
            )

            msg_on_a = _recv_until_type(ws_a, "chat_message")
            assert msg_on_a["content"] == "Hello from A"
            assert msg_on_a["to_user_id"] == user_b["id"]

            msg_on_b = _recv_until_type(ws_b, "chat_message")
            assert msg_on_b["from_user_id"] == user_a["id"]
            assert msg_on_b["content"] == "Hello from A"


def test_offline_recipient_error(client: TestClient) -> None:
    user_a, token_a = _register_user(client, label="sender")
    user_b, _token_b = _register_user(client, label="offline")

    with client.websocket_connect(f"/ws/connect?token={token_a}") as ws_a:
        _recv_until_type(ws_a, "connected")
        _recv_until_type(ws_a, "presence")

        ws_a.send_text(
            json.dumps(
                {
                    "type": "chat_message",
                    "to_user_id": user_b["id"],
                    "content": "Anyone there?",
                }
            )
        )
        error = ws_a.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "user_offline"


def test_validation_error(client: TestClient) -> None:
    _, token = _register_user(client, label="validator")

    with client.websocket_connect(f"/ws/connect?token={token}") as ws:
        _recv_until_type(ws, "connected")
        _recv_until_type(ws, "presence")

        ws.send_text(
            json.dumps(
                {
                    "type": "chat_message",
                    "to_user_id": str(uuid.uuid4()),
                    "content": "   ",
                }
            )
        )
        error = _recv_until_type(ws, "error")
        assert error["code"] == "validation_error"


def test_user_disconnected_event(client: TestClient) -> None:
    user_a, token_a = _register_user(client, label="stay")
    user_b, token_b = _register_user(client, label="leave")

    with client.websocket_connect(f"/ws/connect?token={token_a}") as ws_a:
        _recv_until_type(ws_a, "connected")
        _recv_until_type(ws_a, "presence")

        ws_b = client.websocket_connect(f"/ws/connect?token={token_b}")
        ws_b.__enter__()
        try:
            _recv_until_type(ws_b, "connected")
            _recv_until_type(ws_b, "presence")
            _recv_until_type(ws_a, "user_connected")
        finally:
            ws_b.__exit__(None, None, None)

        disconnected = _recv_until_type(ws_a, "user_disconnected", max_messages=10)
        assert disconnected["user_id"] == user_b["id"]
        assert disconnected["status"] == "offline"

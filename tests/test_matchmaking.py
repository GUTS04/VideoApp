"""Matchmaking queue tests."""

import json

from fastapi.testclient import TestClient

from tests.helpers import register_user as _register


def _drain_bootstrap(ws) -> None:
    assert ws.receive_json()["type"] == "connected"
    assert ws.receive_json()["type"] == "presence"


def _recv_type(ws, expected: str, limit: int = 8) -> dict:
    for _ in range(limit):
        msg = ws.receive_json()
        if msg.get("type") == expected:
            return msg
    raise AssertionError(f"Expected {expected!r} not received")


def test_automatic_match_when_two_users_join(client: TestClient) -> None:
    user_a, token_a = _register(client, label="match_a", gender="male")
    user_b, token_b = _register(client, label="match_b", gender="female")

    with client.websocket_connect(f"/ws/connect?token={token_a}") as ws_a:
        _drain_bootstrap(ws_a)
        ws_a.send_text(json.dumps({"type": "join_queue"}))
        queued = _recv_type(ws_a, "queue_joined")
        assert queued["queue_size"] >= 1

        with client.websocket_connect(f"/ws/connect?token={token_b}") as ws_b:
            _drain_bootstrap(ws_b)
            ws_b.send_text(json.dumps({"type": "join_queue"}))

            match_a = _recv_type(ws_a, "match_found")
            match_b = _recv_type(ws_b, "match_found")

            assert match_a["match_id"] == match_b["match_id"]
            assert match_a["partner"]["user_id"] == user_b["id"]
            assert match_b["partner"]["user_id"] == user_a["id"]


def test_duplicate_queue_entry_rejected(client: TestClient) -> None:
    _, token = _register(client, label="dup")
    with client.websocket_connect(f"/ws/connect?token={token}") as ws:
        _drain_bootstrap(ws)
        ws.send_text(json.dumps({"type": "join_queue"}))
        _recv_type(ws, "queue_joined")
        ws.send_text(json.dumps({"type": "join_queue"}))
        error = _recv_type(ws, "error")
        assert error["code"] == "already_in_queue"


def test_next_partner_requeues_and_rematches(client: TestClient) -> None:
    user_a, token_a = _register(client, label="next_a", gender="male")
    user_b, token_b = _register(client, label="next_b", gender="female")
    user_c, token_c = _register(client, label="next_c", gender="female")

    with client.websocket_connect(f"/ws/connect?token={token_a}") as ws_a:
        _drain_bootstrap(ws_a)
        with client.websocket_connect(f"/ws/connect?token={token_b}") as ws_b:
            _drain_bootstrap(ws_b)
            ws_a.send_text(json.dumps({"type": "join_queue"}))
            _recv_type(ws_a, "queue_joined")
            ws_b.send_text(json.dumps({"type": "join_queue"}))
            _recv_type(ws_a, "match_found")
            _recv_type(ws_b, "match_found")

            with client.websocket_connect(f"/ws/connect?token={token_c}") as ws_c:
                _drain_bootstrap(ws_c)
                ws_c.send_text(json.dumps({"type": "join_queue"}))
                _recv_type(ws_c, "queue_joined")

                ws_a.send_text(json.dumps({"type": "next_partner"}))
                _recv_type(ws_b, "partner_disconnected")

                match_a = _recv_type(ws_a, "match_found")
                match_c = _recv_type(ws_c, "match_found")
                assert match_a["match_id"] == match_c["match_id"]


def test_partner_disconnected_on_socket_close(client: TestClient) -> None:
    user_a, token_a = _register(client, label="stay2", gender="male")
    user_b, token_b = _register(client, label="leave2", gender="female")

    with client.websocket_connect(f"/ws/connect?token={token_a}") as ws_a:
        _drain_bootstrap(ws_a)
        ws_b_ctx = client.websocket_connect(f"/ws/connect?token={token_b}")
        ws_b = ws_b_ctx.__enter__()
        try:
            _drain_bootstrap(ws_b)
            ws_a.send_text(json.dumps({"type": "join_queue"}))
            _recv_type(ws_a, "queue_joined")
            ws_b.send_text(json.dumps({"type": "join_queue"}))
            _recv_type(ws_a, "match_found")
            _recv_type(ws_b, "match_found")
        finally:
            ws_b_ctx.__exit__(None, None, None)

        disconnected = _recv_type(ws_a, "partner_disconnected")
        assert disconnected["partner"]["user_id"] == user_b["id"]
        assert disconnected["reason"] == "disconnect"

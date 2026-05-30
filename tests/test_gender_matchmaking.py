"""Gender-based matchmaking integration tests."""

import json

from fastapi.testclient import TestClient

from tests.helpers import register_user


def _drain_bootstrap(ws) -> None:
    assert ws.receive_json()["type"] == "connected"
    assert ws.receive_json()["type"] == "presence"


def _recv_type(ws, expected: str, limit: int = 8) -> dict:
    for _ in range(limit):
        msg = ws.receive_json()
        if msg.get("type") == expected:
            return msg
    raise AssertionError(f"Expected {expected!r} not received")


def test_male_and_female_match(client: TestClient) -> None:
    male, token_m = register_user(client, label="male_user", gender="male")
    female, token_f = register_user(client, label="female_user", gender="female")

    with client.websocket_connect(f"/ws/connect?token={token_m}") as ws_m:
        _drain_bootstrap(ws_m)
        ws_m.send_text(json.dumps({"type": "join_queue"}))
        _recv_type(ws_m, "queue_joined")

        with client.websocket_connect(f"/ws/connect?token={token_f}") as ws_f:
            _drain_bootstrap(ws_f)
            ws_f.send_text(json.dumps({"type": "join_queue"}))

            match_m = _recv_type(ws_m, "match_found")
            match_f = _recv_type(ws_f, "match_found")

            assert match_m["match_id"] == match_f["match_id"]
            assert match_m["partner"]["user_id"] == female["id"]
            assert match_m["partner"]["gender"] == "female"
            assert match_f["partner"]["user_id"] == male["id"]
            assert match_f["partner"]["gender"] == "male"


def test_same_gender_users_do_not_match(client: TestClient) -> None:
    male_a, token_a = register_user(client, label="male_a", gender="male")
    male_b, token_b = register_user(client, label="male_b", gender="male")

    with client.websocket_connect(f"/ws/connect?token={token_a}") as ws_a:
        _drain_bootstrap(ws_a)
        ws_a.send_text(json.dumps({"type": "join_queue"}))
        _recv_type(ws_a, "queue_joined")

        with client.websocket_connect(f"/ws/connect?token={token_b}") as ws_b:
            _drain_bootstrap(ws_b)
            ws_b.send_text(json.dumps({"type": "join_queue"}))
            _recv_type(ws_b, "queue_joined")

            msg = ws_a.receive_json()
            assert msg["type"] != "match_found"
            assert msg["type"] in ("queue_joined", "presence", "user_connected")


def test_fifo_respects_gender_with_multiple_waiting(client: TestClient) -> None:
    male1, token_m1 = register_user(client, label="m1", gender="male")
    male2, token_m2 = register_user(client, label="m2", gender="male")
    female1, token_f1 = register_user(client, label="f1", gender="female")
    female2, token_f2 = register_user(client, label="f2", gender="female")

    with client.websocket_connect(f"/ws/connect?token={token_m1}") as ws_m1:
        _drain_bootstrap(ws_m1)
        ws_m1.send_text(json.dumps({"type": "join_queue"}))
        _recv_type(ws_m1, "queue_joined")

        with client.websocket_connect(f"/ws/connect?token={token_m2}") as ws_m2:
            _drain_bootstrap(ws_m2)
            ws_m2.send_text(json.dumps({"type": "join_queue"}))
            _recv_type(ws_m2, "queue_joined")

            with client.websocket_connect(f"/ws/connect?token={token_f1}") as ws_f1:
                _drain_bootstrap(ws_f1)
                ws_f1.send_text(json.dumps({"type": "join_queue"}))

                match_m1 = _recv_type(ws_m1, "match_found")
                match_f1 = _recv_type(ws_f1, "match_found")
                assert match_m1["partner"]["user_id"] == female1["id"]
                assert match_f1["partner"]["user_id"] == male1["id"]

                with client.websocket_connect(f"/ws/connect?token={token_f2}") as ws_f2:
                    _drain_bootstrap(ws_f2)
                    ws_f2.send_text(json.dumps({"type": "join_queue"}))

                    match_m2 = _recv_type(ws_m2, "match_found")
                    match_f2 = _recv_type(ws_f2, "match_found")
                    assert match_m2["partner"]["user_id"] == female2["id"]
                    assert match_f2["partner"]["user_id"] == male2["id"]


def test_next_partner_with_gender_constraints(client: TestClient) -> None:
    male, token_m = register_user(client, label="next_m", gender="male")
    female1, token_f1 = register_user(client, label="next_f1", gender="female")
    female2, token_f2 = register_user(client, label="next_f2", gender="female")

    with client.websocket_connect(f"/ws/connect?token={token_m}") as ws_m:
        _drain_bootstrap(ws_m)
        with client.websocket_connect(f"/ws/connect?token={token_f1}") as ws_f1:
            _drain_bootstrap(ws_f1)
            ws_m.send_text(json.dumps({"type": "join_queue"}))
            _recv_type(ws_m, "queue_joined")
            ws_f1.send_text(json.dumps({"type": "join_queue"}))
            _recv_type(ws_m, "match_found")
            _recv_type(ws_f1, "match_found")

            with client.websocket_connect(f"/ws/connect?token={token_f2}") as ws_f2:
                _drain_bootstrap(ws_f2)
                ws_f2.send_text(json.dumps({"type": "join_queue"}))
                _recv_type(ws_f2, "queue_joined")

                ws_m.send_text(json.dumps({"type": "next_partner"}))
                _recv_type(ws_f1, "partner_disconnected")

                match_m = _recv_type(ws_m, "match_found")
                match_f2 = _recv_type(ws_f2, "match_found")
                assert match_m["partner"]["user_id"] == female2["id"]
                assert match_f2["partner"]["user_id"] == male["id"]

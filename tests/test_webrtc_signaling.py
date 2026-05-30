"""WebRTC signaling transport tests (no getUserMedia / peer connection)."""

import json

from fastapi.testclient import TestClient

from tests.helpers import register_user


def _drain_bootstrap(ws) -> None:
    assert ws.receive_json()["type"] == "connected"
    assert ws.receive_json()["type"] == "presence"


def _recv_type(ws, expected: str, limit: int = 10) -> dict:
    for _ in range(limit):
        msg = ws.receive_json()
        if msg.get("type") == expected:
            return msg
    raise AssertionError(f"Expected {expected!r} not received")


def _match_two_users(client: TestClient) -> tuple[dict, str, dict, str, str]:
    male, token_m = register_user(client, label="rtc_m", gender="male")
    female, token_f = register_user(client, label="rtc_f", gender="female")

    ws_m_ctx = client.websocket_connect(f"/ws/connect?token={token_m}")
    ws_m = ws_m_ctx.__enter__()
    _drain_bootstrap(ws_m)
    ws_m.send_text(json.dumps({"type": "join_queue"}))
    _recv_type(ws_m, "queue_joined")

    ws_f_ctx = client.websocket_connect(f"/ws/connect?token={token_f}")
    ws_f = ws_f_ctx.__enter__()
    _drain_bootstrap(ws_f)
    ws_f.send_text(json.dumps({"type": "join_queue"}))

    match_m = _recv_type(ws_m, "match_found")
    _recv_type(ws_f, "match_found")
    match_id = match_m["match_id"]
    return male, token_m, female, token_f, match_id, ws_m, ws_f, ws_m_ctx, ws_f_ctx


def test_webrtc_offer_forwarded_to_matched_partner(client: TestClient) -> None:
    male, _t_m, female, _t_f, match_id, ws_m, ws_f, ctx_m, ctx_f = _match_two_users(client)
    try:
        ws_m.send_text(
            json.dumps(
                {
                    "type": "webrtc_offer",
                    "match_id": match_id,
                    "sdp": {"type": "offer", "sdp": "v=0\r\no=- 0 0 IN IP4 127.0.0.1"},
                }
            )
        )
        offer = _recv_type(ws_f, "webrtc_offer")
        assert offer["match_id"] == match_id
        assert offer["from_user_id"] == male["id"]
        assert offer["sdp"]["type"] == "offer"
        assert "v=0" in offer["sdp"]["sdp"]
    finally:
        ctx_f.__exit__(None, None, None)
        ctx_m.__exit__(None, None, None)


def test_webrtc_answer_and_ice_candidate(client: TestClient) -> None:
    _male, _t_m, _female, _t_f, match_id, ws_m, ws_f, ctx_m, ctx_f = _match_two_users(client)
    try:
        ws_f.send_text(
            json.dumps(
                {
                    "type": "webrtc_answer",
                    "sdp": {"type": "answer", "sdp": "v=0\r\no=- 0 0 IN IP4 127.0.0.1"},
                }
            )
        )
        answer = _recv_type(ws_m, "webrtc_answer")
        assert answer["match_id"] == match_id
        assert answer["sdp"]["type"] == "answer"

        ws_m.send_text(
            json.dumps(
                {
                    "type": "ice_candidate",
                    "candidate": {
                        "candidate": "candidate:1 1 UDP 2130706431 192.168.0.1 49200 typ host",
                        "sdpMid": "0",
                        "sdpMLineIndex": 0,
                    },
                }
            )
        )
        ice = _recv_type(ws_f, "ice_candidate")
        assert ice["match_id"] == match_id
        assert ice["candidate"]["sdpMid"] == "0"
        assert "typ host" in ice["candidate"]["candidate"]
    finally:
        ctx_f.__exit__(None, None, None)
        ctx_m.__exit__(None, None, None)


def test_signaling_rejected_when_not_matched(client: TestClient) -> None:
    _, token = register_user(client, label="rtc_solo")
    with client.websocket_connect(f"/ws/connect?token={token}") as ws:
        _drain_bootstrap(ws)
        ws.send_text(
            json.dumps(
                {
                    "type": "webrtc_offer",
                    "sdp": {"type": "offer", "sdp": "v=0"},
                }
            )
        )
        error = _recv_type(ws, "error")
        assert error["code"] == "not_in_match"


def test_signaling_rejected_for_wrong_match_id(client: TestClient) -> None:
    _male, _t_m, _female, _t_f, match_id, ws_m, ws_f, ctx_m, ctx_f = _match_two_users(client)
    try:
        ws_m.send_text(
            json.dumps(
                {
                    "type": "webrtc_offer",
                    "match_id": "00000000-0000-0000-0000-000000000099",
                    "sdp": {"type": "offer", "sdp": "v=0"},
                }
            )
        )
        error = _recv_type(ws_m, "error")
        assert error["code"] == "invalid_message"
    finally:
        ctx_f.__exit__(None, None, None)
        ctx_m.__exit__(None, None, None)


def test_signaling_validation_error(client: TestClient) -> None:
    _male, _t_m, _female, _t_f, _match_id, ws_m, ws_f, ctx_m, ctx_f = _match_two_users(client)
    try:
        ws_m.send_text(json.dumps({"type": "webrtc_offer", "sdp": {"type": "offer", "sdp": ""}}))
        error = _recv_type(ws_m, "error")
        assert error["code"] == "validation_error"
    finally:
        ctx_f.__exit__(None, None, None)
        ctx_m.__exit__(None, None, None)

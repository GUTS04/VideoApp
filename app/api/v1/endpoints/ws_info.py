from fastapi import APIRouter, Depends

from app.api.deps import get_current_active_user
from app.core.config import get_settings
from app.models.user import User
from app.matchmaking.service import matchmaking_service
from app.websocket.manager import manager

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.get(
    "/connection-info",
    summary="WebSocket connection & messaging guide",
    description="""
## Authenticated WebSocket + direct messaging

### 1. Obtain JWT
`POST /api/v1/auth/register` or `POST /api/v1/auth/login` → copy `tokens.access_token`.

### 2. Connect
```
ws://127.0.0.1:8001/ws/connect?token=<access_token>
```

### 3. Server events (JSON)

| Event | When |
|-------|------|
| `connected` | You connected; includes `online_users` |
| `presence` | Snapshot of all online users |
| `user_connected` | Another user came online |
| `user_disconnected` | Another user went offline |
| `chat_message` | Direct message sent or received |
| `error` | Validation / offline / not found |
| `pong` | Reply to `ping` |

### 4. Send a direct message (JSON text frame)
```json
{
  "type": "chat_message",
  "to_user_id": "recipient-uuid-here",
  "content": "Hello!"
}
```

### 5. Two-browser-tab test
1. Register **User A** in tab 1 → login → copy `user_id` + token → connect WebSocket.
2. Register **User B** in tab 2 → login → connect WebSocket.
3. Tab A receives `user_connected` for B; send `chat_message` with B's `user_id`.
4. Tab B receives `chat_message` in real time.

**Offline:** If recipient has no active WebSocket, sender gets `error` with `code: user_offline`.

### 6. Matchmaking (queue)

| Client sends | Server responds |
|--------------|-----------------|
| `{"type":"join_queue"}` | `queue_joined` or `match_found` |
| `{"type":"leave_queue"}` | `queue_left` |
| `{"type":"next_partner"}` | `partner_disconnected` (to partner) + `queue_joined` or `match_found` |

| Server event | Meaning |
|--------------|---------|
| `match_found` | Paired with a partner (`match_id`, `partner`) |
| `partner_disconnected` | Partner left, disconnected, or clicked next |

### 7. WebRTC signaling (matched sessions only)

After `match_found`, exchange SDP/ICE with your **current partner only**:

| Client sends | Partner receives |
|--------------|------------------|
| `webrtc_offer` | `webrtc_offer` |
| `webrtc_answer` | `webrtc_answer` |
| `ice_candidate` | `ice_candidate` |

Unmatched users get `error` with `code: not_in_match`. Signaling is **not** echoed to the sender.

WebSockets cannot be tested inside Swagger UI; use browser DevTools or pytest.
    """,
)
def websocket_connection_info() -> dict:
    settings = get_settings()
    host = settings.host if settings.host != "0.0.0.0" else "127.0.0.1"
    ws_url = f"ws://{host}:{settings.port}/ws/connect?token=<access_token>"

    return {
        "websocket_url": ws_url,
        "authentication": {
            "methods": [
                "Query parameter: ?token=<access_token>",
                "Header: Authorization: Bearer <access_token>",
            ],
            "token_source": "POST /api/v1/auth/login or /api/v1/auth/register",
        },
        "connection_flow": [
            "Obtain JWT access_token",
            "Open WebSocket /ws/connect?token=...",
            "Receive connected + presence events",
            "Send chat_message JSON to another user's UUID",
            "Receive real-time chat_message or error events",
        ],
        "client_send_examples": {
            "chat_message": {
                "type": "chat_message",
                "to_user_id": "00000000-0000-0000-0000-000000000002",
                "content": "Hello!",
            },
            "join_queue": {"type": "join_queue"},
            "leave_queue": {"type": "leave_queue"},
            "next_partner": {"type": "next_partner"},
            "webrtc_offer": {
                "type": "webrtc_offer",
                "match_id": "active-match-uuid",
                "sdp": {"type": "offer", "sdp": "v=0..."},
            },
            "webrtc_answer": {
                "type": "webrtc_answer",
                "sdp": {"type": "answer", "sdp": "v=0..."},
            },
            "ice_candidate": {
                "type": "ice_candidate",
                "candidate": {
                    "candidate": "candidate:1 1 UDP 2130706431 192.168.0.1 9 typ host",
                    "sdpMid": "0",
                    "sdpMLineIndex": 0,
                },
            },
            "ping": {"type": "ping"},
        },
        "server_events": {
            "connected": "Your session is ready; includes online_users list",
            "presence": "Online users snapshot",
            "user_connected": "Another user came online (first connection only)",
            "user_disconnected": "Another user went fully offline",
            "chat_message": "Direct message payload (delivered to sender and recipient)",
            "error": "codes: invalid_json, validation_error, user_not_found, user_offline, self_message, unknown_type",
            "pong": "Reply to ping",
            "queue_joined": "Waiting for a partner in the queue",
            "queue_left": "Left the matchmaking queue",
            "match_found": "Matched with a partner",
            "partner_disconnected": "Partner left or requested next match",
            "webrtc_offer": "Forwarded from matched partner (SDP offer)",
            "webrtc_answer": "Forwarded from matched partner (SDP answer)",
            "ice_candidate": "Forwarded ICE candidate from matched partner",
        },
        "webrtc_rules": {
            "requires_active_match": True,
            "forward_to": "current_matched_partner_only",
            "echo_to_sender": False,
            "invalid_match_id": "error if match_id does not match active session",
        },
        "matchmaking_rules": {
            "one_match_per_user": True,
            "no_duplicate_queue_entries": True,
            "no_self_match": True,
            "fifo_matching": "First waiting opposite-gender user is paired on join_queue",
            "gender_pairing": "male matches female only; female matches male only",
            "register_requires_gender": "POST /api/v1/auth/register must include gender: male | female",
        },
        "online_offline_rules": {
            "online": "At least one active WebSocket for that user_id",
            "offline": "No active WebSockets; chat_message returns error user_offline",
            "multi_tab": "user_connected fires once; user_disconnected when last tab closes",
        },
    }


@router.get(
    "/status",
    summary="WebSocket connection status (authenticated)",
    description="Returns in-memory connection stats. Requires JWT (HTTP Bearer).",
)
def websocket_status(
    _: User = Depends(get_current_active_user),
) -> dict:
    return {
        "active_connections": manager.connection_count,
        "unique_users_online": manager.unique_user_count,
        "connected_user_ids": manager.get_connected_user_ids(),
        "online_users": manager.get_online_users(),
        "connections": manager.snapshot(),
        "matchmaking": matchmaking_service.status_snapshot(),
    }

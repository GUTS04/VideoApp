import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database.session import SessionLocal
from app.websocket.auth import WebSocketAuthError, authenticate_websocket
from app.websocket.handlers import MessagingHandler
from app.websocket.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

WS_CLOSE_POLICY_VIOLATION = 1008


@router.websocket("/ws/connect")
async def websocket_connect(websocket: WebSocket) -> None:
    """
    Authenticated WebSocket with real-time direct messaging.

    **Auth:** `ws://host/ws/connect?token=<access_token>`

    **Send (JSON):**
    ```json
    {"type": "chat_message", "to_user_id": "<uuid>", "content": "Hello"}
    ```

    **Events (server → client):** `connected`, `presence`, `user_connected`,
    `user_disconnected`, `chat_message`, `queue_joined`, `match_found`,
    `partner_disconnected`, `webrtc_offer`, `webrtc_answer`, `ice_candidate`,
    `error`, `pong`

    **Matchmaking:** `join_queue`, `leave_queue`, `next_partner`

    **WebRTC signaling (matched only):** `webrtc_offer`, `webrtc_answer`, `ice_candidate`

    See `GET /api/v1/ws/connection-info` for the full flow.
    """
    db = SessionLocal()
    connection_id: str | None = None
    handler: MessagingHandler | None = None

    try:
        user = authenticate_websocket(websocket, db)
    except WebSocketAuthError as exc:
        logger.info("WebSocket auth rejected: %s", exc)
        await websocket.close(code=WS_CLOSE_POLICY_VIOLATION, reason=str(exc))
        return
    finally:
        db.close()

    client = await manager.connect(user, websocket)
    connection_id = client.connection_id
    handler = MessagingHandler(connection_id=connection_id, user=user, ws_manager=manager)

    try:
        await handler.on_connect()

        while True:
            raw = await websocket.receive_text()
            await handler.handle_raw_message(raw)

    except WebSocketDisconnect:
        logger.debug("Client disconnected connection_id=%s", connection_id)
    except Exception:
        logger.exception("WebSocket error connection_id=%s", connection_id)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass
    finally:
        if connection_id:
            manager.disconnect(connection_id)
        if handler:
            await handler.on_disconnect()

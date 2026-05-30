import json
import logging
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.user import User
from app.schemas.ws_messages import (
    ChatMessageEvent,
    ConnectedEvent,
    ErrorCode,
    ErrorEvent,
    IncomingChatMessage,
    IncomingPingMessage,
    OnlineUser,
    PongEvent,
    PresenceEvent,
    UserConnectedEvent,
    UserDisconnectedEvent,
    utc_now_iso,
)
from app.schemas.matchmaking import (
    IncomingJoinQueue,
    IncomingLeaveQueue,
    IncomingNextPartner,
)
from app.services.user import UserService
from app.websocket.manager import ConnectionManager, manager

logger = logging.getLogger(__name__)


class MessagingHandler:
    """Direct messaging over authenticated WebSockets."""

    def __init__(self, *, connection_id: str, user: User, ws_manager: ConnectionManager) -> None:
        self.connection_id = connection_id
        self.user = user
        self.manager = ws_manager

    async def send_event(self, connection_id: str, payload: dict[str, Any]) -> None:
        await self.manager.send_json(connection_id, payload)

    async def send_error(
        self,
        code: ErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        event = ErrorEvent(code=code, message=message, details=details)
        await self.send_event(self.connection_id, event.model_dump())

    async def on_connect(self) -> None:
        online = [OnlineUser(**u) for u in self.manager.get_online_users()]

        connected = ConnectedEvent(
            connection_id=self.connection_id,
            user_id=str(self.user.id),
            username=self.user.username,
            online_users=online,
        )
        await self.send_event(self.connection_id, connected.model_dump())

        presence = PresenceEvent(online_users=online)
        await self.send_event(self.connection_id, presence.model_dump())

        if self.manager.connection_count_for_user(self.user.id) == 1:
            announcement = UserConnectedEvent(
                user_id=str(self.user.id),
                username=self.user.username,
            )
            await self.manager.broadcast(
                announcement.model_dump(),
                exclude_connection_id=self.connection_id,
            )

    async def on_disconnect(self) -> None:
        if not self.manager.is_user_online(self.user.id):
            from app.matchmaking.service import matchmaking_service

            await matchmaking_service.handle_user_offline(self.user.id, self.manager)
            announcement = UserDisconnectedEvent(
                user_id=str(self.user.id),
                username=self.user.username,
            )
            await self.manager.broadcast(announcement.model_dump())

    async def handle_raw_message(self, raw: str) -> None:
        if raw.strip().lower() == "ping":
            await self.send_event(self.connection_id, PongEvent().model_dump())
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            await self.send_error(ErrorCode.INVALID_JSON, "Message must be valid JSON")
            return

        if not isinstance(data, dict):
            await self.send_error(ErrorCode.INVALID_MESSAGE, "Message must be a JSON object")
            return

        message_type = data.get("type")
        if message_type == "chat_message":
            await self._handle_chat_message(data)
        elif message_type == "ping":
            IncomingPingMessage.model_validate(data)
            await self.send_event(self.connection_id, PongEvent().model_dump())
        elif message_type == "join_queue":
            await self._handle_join_queue(data)
        elif message_type == "leave_queue":
            await self._handle_leave_queue(data)
        elif message_type == "next_partner":
            await self._handle_next_partner(data)
        elif message_type == "webrtc_offer":
            await self._handle_webrtc_offer(data)
        elif message_type == "webrtc_answer":
            await self._handle_webrtc_answer(data)
        elif message_type == "ice_candidate":
            await self._handle_ice_candidate(data)
        else:
            await self.send_error(
                ErrorCode.UNKNOWN_TYPE,
                f"Unknown message type: {message_type!r}",
            )

    async def _handle_chat_message(self, data: dict[str, Any]) -> None:
        try:
            incoming = IncomingChatMessage.model_validate(data)
        except ValidationError as exc:
            await self.send_error(
                ErrorCode.VALIDATION_ERROR,
                "Invalid chat_message payload",
                details={
                    "fields": [
                        ".".join(str(part) for part in err.get("loc", ()))
                        for err in exc.errors()
                    ]
                },
            )
            return

        if incoming.to_user_id == self.user.id:
            await self.send_error(ErrorCode.SELF_MESSAGE, "Cannot send a message to yourself")
            return

        db: Session = SessionLocal()
        try:
            recipient = UserService.get_by_id(db, incoming.to_user_id)
        finally:
            db.close()

        if not recipient:
            await self.send_error(
                ErrorCode.USER_NOT_FOUND,
                "Recipient user does not exist",
                details={"to_user_id": str(incoming.to_user_id)},
            )
            return

        if not self.manager.is_user_online(recipient.id):
            await self.send_error(
                ErrorCode.USER_OFFLINE,
                "Recipient is offline",
                details={
                    "to_user_id": str(recipient.id),
                    "to_username": recipient.username,
                    "status": "offline",
                },
            )
            return

        message_id = str(uuid.uuid4())
        event = ChatMessageEvent(
            message_id=message_id,
            from_user_id=str(self.user.id),
            from_username=self.user.username,
            to_user_id=str(recipient.id),
            content=incoming.content,
            sent_at=utc_now_iso(),
        )
        payload = event.model_dump()

        delivered = await self.manager.send_to_user(recipient.id, payload)
        if delivered == 0:
            await self.send_error(
                ErrorCode.USER_OFFLINE,
                "Recipient went offline before delivery",
                details={"to_user_id": str(recipient.id), "status": "offline"},
            )
            return

        await self.send_event(self.connection_id, payload)
        logger.info(
            "chat_message %s -> %s (%s)",
            self.user.id,
            recipient.id,
            message_id,
        )

    async def _handle_join_queue(self, data: dict[str, Any]) -> None:
        from app.matchmaking.service import matchmaking_service

        try:
            IncomingJoinQueue.model_validate(data)
        except ValidationError as exc:
            await self._validation_error(exc)
            return
        error = await matchmaking_service.join_queue(self.user, self.manager)
        if error:
            await self.send_event(self.connection_id, error)

    async def _handle_leave_queue(self, data: dict[str, Any]) -> None:
        from app.matchmaking.service import matchmaking_service

        try:
            IncomingLeaveQueue.model_validate(data)
        except ValidationError as exc:
            await self._validation_error(exc)
            return
        error = await matchmaking_service.leave_queue(self.user, self.manager)
        if error:
            await self.send_event(self.connection_id, error)

    async def _handle_next_partner(self, data: dict[str, Any]) -> None:
        from app.matchmaking.service import matchmaking_service

        try:
            IncomingNextPartner.model_validate(data)
        except ValidationError as exc:
            await self._validation_error(exc)
            return
        error = await matchmaking_service.next_partner(self.user, self.manager)
        if error:
            await self.send_event(self.connection_id, error)

    async def _handle_webrtc_offer(self, data: dict[str, Any]) -> None:
        from app.matchmaking.service import matchmaking_service
        from app.webrtc.signaling_service import WebRtcSignalingService

        signaling = WebRtcSignalingService(matchmaking_service.matches)
        error = await signaling.handle_offer(self.user, data, self.manager)
        if error:
            await self.send_event(self.connection_id, error)

    async def _handle_webrtc_answer(self, data: dict[str, Any]) -> None:
        from app.matchmaking.service import matchmaking_service
        from app.webrtc.signaling_service import WebRtcSignalingService

        signaling = WebRtcSignalingService(matchmaking_service.matches)
        error = await signaling.handle_answer(self.user, data, self.manager)
        if error:
            await self.send_event(self.connection_id, error)

    async def _handle_ice_candidate(self, data: dict[str, Any]) -> None:
        from app.matchmaking.service import matchmaking_service
        from app.webrtc.signaling_service import WebRtcSignalingService

        signaling = WebRtcSignalingService(matchmaking_service.matches)
        error = await signaling.handle_ice_candidate(self.user, data, self.manager)
        if error:
            await self.send_event(self.connection_id, error)

    async def _validation_error(self, exc: ValidationError) -> None:
        await self.send_error(
            ErrorCode.VALIDATION_ERROR,
            "Invalid message payload",
            details={
                "fields": [
                    ".".join(str(part) for part in err.get("loc", ()))
                    for err in exc.errors()
                ]
            },
        )

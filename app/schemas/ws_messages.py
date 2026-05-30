import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WsEventType(StrEnum):
    CONNECTED = "connected"
    PRESENCE = "presence"
    USER_CONNECTED = "user_connected"
    USER_DISCONNECTED = "user_disconnected"
    CHAT_MESSAGE = "chat_message"
    ERROR = "error"
    PONG = "pong"


class ErrorCode(StrEnum):
    INVALID_JSON = "invalid_json"
    INVALID_MESSAGE = "invalid_message"
    VALIDATION_ERROR = "validation_error"
    USER_NOT_FOUND = "user_not_found"
    USER_OFFLINE = "user_offline"
    SELF_MESSAGE = "self_message"
    UNKNOWN_TYPE = "unknown_type"
    ALREADY_IN_QUEUE = "already_in_queue"
    NOT_IN_QUEUE = "not_in_queue"
    ALREADY_IN_MATCH = "already_in_match"
    NOT_IN_MATCH = "not_in_match"
    MATCH_FAILED = "match_failed"


# --- Client → server ---


class IncomingChatMessage(BaseModel):
    """Send a direct message to another user."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "chat_message",
                    "to_user_id": "00000000-0000-0000-0000-000000000002",
                    "content": "Hello!",
                }
            ]
        }
    )

    type: Literal["chat_message"] = "chat_message"
    to_user_id: uuid.UUID
    content: str = Field(..., min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message content cannot be empty")
        return stripped


class IncomingPingMessage(BaseModel):
    type: Literal["ping"] = "ping"


# --- Server → client ---


class OnlineUser(BaseModel):
    user_id: str
    username: str
    status: Literal["online"] = "online"


class ConnectedEvent(BaseModel):
    type: Literal["connected"] = "connected"
    connection_id: str
    user_id: str
    username: str
    message: str = "Authenticated WebSocket connection established"
    online_users: list[OnlineUser] = Field(default_factory=list)


class PresenceEvent(BaseModel):
    type: Literal["presence"] = "presence"
    online_users: list[OnlineUser]


class UserConnectedEvent(BaseModel):
    type: Literal["user_connected"] = "user_connected"
    user_id: str
    username: str
    status: Literal["online"] = "online"


class UserDisconnectedEvent(BaseModel):
    type: Literal["user_disconnected"] = "user_disconnected"
    user_id: str
    username: str
    status: Literal["offline"] = "offline"


class ChatMessageEvent(BaseModel):
    type: Literal["chat_message"] = "chat_message"
    message_id: str
    from_user_id: str
    from_username: str
    to_user_id: str
    content: str
    sent_at: str


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None


class PongEvent(BaseModel):
    type: Literal["pong"] = "pong"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()

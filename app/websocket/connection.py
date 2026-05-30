import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import WebSocket


@dataclass
class ConnectedClient:
    """A single authenticated WebSocket connection."""

    connection_id: str
    user_id: uuid.UUID
    username: str
    websocket: WebSocket
    connected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

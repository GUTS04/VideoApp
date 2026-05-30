import json
import logging
import uuid
from typing import Any

from fastapi import WebSocket

from app.models.user import User
from app.websocket.connection import ConnectedClient

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    In-memory registry of authenticated WebSocket connections.
    Supports multiple concurrent connections per user (e.g. multiple tabs).
    """

    def __init__(self) -> None:
        self._connections: dict[str, ConnectedClient] = {}
        self._user_connection_ids: dict[uuid.UUID, set[str]] = {}

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    @property
    def unique_user_count(self) -> int:
        return len(self._user_connection_ids)

    def get_connection_ids_for_user(self, user_id: uuid.UUID) -> set[str]:
        return set(self._user_connection_ids.get(user_id, set()))

    def get_connected_user_ids(self) -> list[str]:
        return [str(user_id) for user_id in self._user_connection_ids]

    def is_user_online(self, user_id: uuid.UUID) -> bool:
        return bool(self._user_connection_ids.get(user_id))

    def get_online_users(self) -> list[dict[str, str]]:
        """Unique online users (one entry per user_id)."""
        seen: dict[uuid.UUID, dict[str, str]] = {}
        for client in self._connections.values():
            if client.user_id not in seen:
                seen[client.user_id] = {
                    "user_id": str(client.user_id),
                    "username": client.username,
                    "status": "online",
                }
        return list(seen.values())

    def connection_count_for_user(self, user_id: uuid.UUID) -> int:
        return len(self._user_connection_ids.get(user_id, set()))

    def get_connection(self, connection_id: str) -> ConnectedClient | None:
        return self._connections.get(connection_id)

    async def connect(self, user: User, websocket: WebSocket) -> ConnectedClient:
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        client = ConnectedClient(
            connection_id=connection_id,
            user_id=user.id,
            username=user.username,
            websocket=websocket,
        )
        self._connections[connection_id] = client
        self._user_connection_ids.setdefault(user.id, set()).add(connection_id)
        logger.info(
            "WebSocket connected user_id=%s connection_id=%s (total=%s)",
            user.id,
            connection_id,
            self.connection_count,
        )
        return client

    def disconnect(self, connection_id: str) -> None:
        client = self._connections.pop(connection_id, None)
        if not client:
            return

        user_connections = self._user_connection_ids.get(client.user_id)
        if user_connections:
            user_connections.discard(connection_id)
            if not user_connections:
                del self._user_connection_ids[client.user_id]

        logger.info(
            "WebSocket disconnected user_id=%s connection_id=%s (total=%s)",
            client.user_id,
            connection_id,
            self.connection_count,
        )

    async def send_json(self, connection_id: str, data: dict[str, Any]) -> bool:
        client = self._connections.get(connection_id)
        if not client:
            return False
        try:
            await client.websocket.send_text(json.dumps(data))
            return True
        except Exception:
            logger.warning("Send failed; removing connection_id=%s", connection_id)
            self.disconnect(connection_id)
            return False

    async def send_to_user(self, user_id: uuid.UUID, data: dict[str, Any]) -> int:
        sent = 0
        for connection_id in list(self.get_connection_ids_for_user(user_id)):
            if await self.send_json(connection_id, data):
                sent += 1
        return sent

    async def broadcast(
        self,
        data: dict[str, Any],
        *,
        exclude_connection_id: str | None = None,
    ) -> None:
        message = json.dumps(data)
        for connection_id, client in list(self._connections.items()):
            if connection_id == exclude_connection_id:
                continue
            try:
                await client.websocket.send_text(message)
            except Exception:
                self.disconnect(connection_id)

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "connection_id": client.connection_id,
                "user_id": str(client.user_id),
                "username": client.username,
                "connected_at": client.connected_at.isoformat(),
            }
            for client in self._connections.values()
        ]


manager = ConnectionManager()

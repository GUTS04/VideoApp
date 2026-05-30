import uuid

import jwt
from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.models.user import User
from app.services.user import UserService


class WebSocketAuthError(Exception):
    """Raised when WebSocket JWT authentication fails."""


def extract_bearer_token(websocket: WebSocket) -> str | None:
    """
    Resolve JWT from query `token` or `Authorization: Bearer <jwt>` header.
    Query param is recommended for browser WebSocket clients.
    """
    token = websocket.query_params.get("token")
    if token:
        return token.strip()

    authorization = websocket.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()

    return None


def authenticate_websocket(websocket: WebSocket, db: Session) -> User:
    """
    Validate JWT access token and return the active user.
    Call before accepting the socket when possible; on failure raise WebSocketAuthError.
    """
    token = extract_bearer_token(websocket)
    if not token:
        raise WebSocketAuthError("Missing token. Pass ?token=<access_token> or Authorization header.")

    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise WebSocketAuthError("Invalid or expired access token") from exc

    user = UserService.get_by_id(db, user_id)
    if not user:
        raise WebSocketAuthError("User not found")
    if not user.is_active:
        raise WebSocketAuthError("Inactive user account")

    return user

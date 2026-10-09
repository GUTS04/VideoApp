from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/ice")
def get_ice_servers() -> dict:
    """Public ICE server configuration for WebRTC clients."""
    settings = get_settings()
    servers: list[dict] = [{"urls": "stun:stun.l.google.com:19302"}]

    if settings.turn_urls.strip():
        for url in settings.turn_urls.split(","):
            entry: dict = {"urls": url.strip()}
            if settings.turn_username:
                entry["username"] = settings.turn_username
            if settings.turn_credential:
                entry["credential"] = settings.turn_credential
            servers.append(entry)

    return {"iceServers": servers}

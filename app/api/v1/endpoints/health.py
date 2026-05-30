from fastapi import APIRouter

from app.core.config import get_settings
from app.database.session import check_database_connection
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    db_ok = check_database_connection()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        app=settings.app_name,
        environment=settings.app_env,
        database="connected" if db_ok else "disconnected",
    )

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.websocket.router import router as websocket_router

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s [%s]", settings.app_name, settings.app_env)
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        description=(
            "VideoApp API with JWT authentication and WebSockets.\n\n"
            "**HTTP:** Register or login, copy `access_token`, click **Authorize**, "
            "then call `/auth/me` and `/users`.\n\n"
            "**WebSocket:** Read `GET /api/v1/ws/connection-info` for the full flow, "
            "then connect to `ws://HOST:PORT/ws/connect?token=<access_token>`."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(websocket_router)

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {
            "message": "VideoApp API",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


app = create_app()

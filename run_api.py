"""Start the FastAPI server using host/port from .env."""

import uvicorn

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.app_env == "development",
        reload_dirs=["app"],
    )


if __name__ == "__main__":
    main()

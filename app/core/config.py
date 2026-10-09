from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "VideoApp API"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: str = Field(
        default="dev-only-change-in-production-min-16-chars",
        min_length=16,
    )

    host: str = "127.0.0.1"
    port: int = 8001

    postgres_user: str = "videoapp"
    postgres_password: str = "videoapp"
    postgres_db: str = "videoapp"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    initial_coin_balance: int = 500

    turn_urls: str = ""
    turn_username: str = ""
    turn_credential: str = ""

    @property
    def effective_jwt_secret(self) -> str:
        return self.jwt_secret_key or self.secret_key

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg2",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=f"/{self.postgres_db}",
            )
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

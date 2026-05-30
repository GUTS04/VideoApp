"""Test database connection using .env (no password printed)."""

from urllib.parse import urlparse

from app.core.config import get_settings
from app.database.session import check_database_connection


def main() -> None:
    settings = get_settings()
    parsed = urlparse(settings.sqlalchemy_database_uri.replace("+psycopg2", ""))
    user = parsed.username or "?"
    host = parsed.hostname or "?"
    port = parsed.port or 5432
    database = (parsed.path or "/").lstrip("/") or "?"

    print(f"Trying: user={user} host={host} port={port} database={database}")

    if check_database_connection():
        print("SUCCESS — database connection works.")
    else:
        print("FAILED — wrong password, user, or database name.")
        print("Fix DATABASE_URL in .env to match what works in pgAdmin.")


if __name__ == "__main__":
    main()

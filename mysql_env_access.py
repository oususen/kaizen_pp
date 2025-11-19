"""
Helpers for bootstrapping a SQLAlchemy engine from the .env-managed MySQL settings.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config import get_mysql_settings

REQUIRED_FIELDS = ("host", "user", "password")


@dataclass
class MySQLSettings:
    """Container holding the resolved MySQL connection parameters."""

    host: str
    port: str
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "MySQLSettings":
        """Read values from .env via config.get_mysql_settings()."""
        values = get_mysql_settings()
        missing = [field for field in REQUIRED_FIELDS if not values.get(field)]
        if missing:
            raise ValueError(
                "Missing MySQL .env entries: " + ", ".join(missing)
            )
        return cls(
            host=cast(str, values["host"]),
            port=cast(str, values["port"]),
            user=cast(str, values["user"]),
            password=cast(str, values["password"]),
            database=cast(str, values["database"]),
        )

    def to_sqlalchemy_url(self) -> str:
        """Return a PyMySQL-based SQLAlchemy URL."""
        return (
            f"mysql+pymysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}?charset=utf8mb4"
        )


def create_mysql_engine_from_env() -> Engine:
    """Build a SQLAlchemy engine configured via the .env settings."""
    settings = MySQLSettings.from_env()
    return create_engine(settings.to_sqlalchemy_url(), pool_pre_ping=True)


if __name__ == "__main__":
    # Lightweight smoke test for quick validation during development.
    try:
        engine = create_mysql_engine_from_env()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Successfully connected to MySQL.")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"MySQL connection failed: {exc}")

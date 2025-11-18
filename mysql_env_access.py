"""
Helpers for bootstrapping a SQLAlchemy engine from MySQL-related environment variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

PRIMARY_DB_KEYS = {
    "host": "PRIMARY_DB_HOST",
    "port": "PRIMARY_DB_PORT",
    "user": "PRIMARY_DB_USER",
    "password": "PRIMARY_DB_PASSWORD",
    "database": "PRIMARY_DB_NAME",
}
DEFAULT_PORT = "3306"
DEFAULT_DATABASE = "kaizen_db"


@dataclass
class MySQLSettings:
    """Container holding the resolved MySQL connection parameters."""

    host: str
    port: str
    user: str
    password: str
    database: str = DEFAULT_DATABASE

    @classmethod
    def from_env(cls) -> "MySQLSettings":
        """
        Read the PRIMARY_DB_* environment variables and build a settings object.

        Raises:
            ValueError: When any of host/user/password is missing.
        """
        values: Dict[str, Optional[str]] = {
            field: os.getenv(env_name) for field, env_name in PRIMARY_DB_KEYS.items()
        }
        missing = [
            field for field in ("host", "user", "password") if not values.get(field)
        ]
        if missing:
            raise ValueError(
                "Missing MySQL environment variables: "
                + ", ".join(PRIMARY_DB_KEYS[field] for field in missing)
            )
        values["port"] = values.get("port") or DEFAULT_PORT
        values["database"] = values.get("database") or DEFAULT_DATABASE
        return cls(**values)  # type: ignore[arg-type]

    def to_sqlalchemy_url(self) -> str:
        """Return a PyMySQL-based SQLAlchemy URL."""
        return (
            f"mysql+pymysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}?charset=utf8mb4"
        )


def create_mysql_engine_from_env() -> Engine:
    """
    Build a SQLAlchemy engine configured for the PRIMARY_DB_* environment variables.

    Example:

        >>> engine = create_mysql_engine_from_env()
        >>> with engine.connect() as conn:
        ...     conn.execute(text("SELECT 1"))
    """
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

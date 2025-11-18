"""Application-wide configuration helpers."""
from __future__ import annotations

import os
from typing import Dict, Optional

from dotenv import load_dotenv

# Load values from .env when present so local development "just works".
load_dotenv(override=False)

# Environment variables used for the primary MySQL connection.
PRIMARY_DB_ENV = {
    "host": "PRIMARY_DB_HOST",
    "port": "PRIMARY_DB_PORT",
    "user": "PRIMARY_DB_USER",
    "password": "PRIMARY_DB_PASSWORD",
    "database": "PRIMARY_DB_NAME",
}
DEFAULT_PORT = "3306"
DEFAULT_DATABASE = "kaizen_db"


def _get_env(name: str) -> Optional[str]:
    """Return the value of an environment variable, treating blanks as missing."""
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def get_mysql_settings() -> Dict[str, Optional[str]]:
    """
    Collect MySQL connection settings from environment variables.

    Host, user, and password remain optional so that callers can decide how to
    handle missing credentials, while port/database fall back to safe defaults.
    """
    settings: Dict[str, Optional[str]] = {
        field: _get_env(env_name) for field, env_name in PRIMARY_DB_ENV.items()
    }
    settings["port"] = settings.get("port") or DEFAULT_PORT
    settings["database"] = settings.get("database") or DEFAULT_DATABASE
    return settings

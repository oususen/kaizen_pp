"""Application-wide configuration helpers."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import dotenv_values

# Load settings strictly from .env placed at the project root.
ENV_PATH = Path(__file__).resolve().parent / ".env"
ENV_VALUES = dotenv_values(dotenv_path=ENV_PATH)

# Keys expected inside the .env file for the MySQL connection.
PRIMARY_DB_ENV = {
    "host": "PRIMARY_DB_HOST",
    "port": "PRIMARY_DB_PORT",
    "user": "PRIMARY_DB_USER",
    "password": "PRIMARY_DB_PASSWORD",
    "database": "PRIMARY_DB_NAME",
}
DEFAULT_PORT = "3306"
DEFAULT_DATABASE = "kaizen_db"
PASSWORD_FIELDS = {"password"}


def _normalize(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _get_env(name: str, prefer_system: bool = False) -> Optional[str]:
    """Return an environment variable value."""
    if prefer_system:
        system_value = _normalize(os.getenv(name))
        if system_value is not None:
            return system_value
    return _normalize(ENV_VALUES.get(name))


def get_mysql_settings() -> Dict[str, Optional[str]]:
    """
    Collect MySQL connection settings.

    Host, user, and database metadata are sourced from .env, while sensitive
    values (currently the password) may optionally be injected via OS-level
    environment variables to keep them out of local files.
    """
    settings: Dict[str, Optional[str]] = {}
    for field, env_name in PRIMARY_DB_ENV.items():
        settings[field] = _get_env(env_name, prefer_system=field in PASSWORD_FIELDS)
    settings["port"] = settings.get("port") or DEFAULT_PORT
    settings["database"] = settings.get("database") or DEFAULT_DATABASE
    return settings

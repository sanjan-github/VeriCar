from __future__ import annotations

import os
from typing import Mapping
from urllib.parse import urlparse


class ConfigurationError(ValueError):
    """Raised when environment configuration contains invalid values."""


def env_str(
    key: str,
    default: str,
    *,
    env: Mapping[str, str] | None = None,
    allowed: set[str] | None = None,
) -> str:
    source = env if env is not None else os.environ
    val = source.get(key, default)
    if val is None or not val.strip():
        val = default
    val = val.strip()
    if allowed is not None and val not in allowed:
        raise ConfigurationError(
            f"Invalid {key}: '{val}' must be one of {sorted(allowed)}"
        )
    return val


def env_int(
    key: str,
    default: int,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    source = env if env is not None else os.environ
    raw = source.get(key)
    if raw is None or not raw.strip():
        val = default
    else:
        try:
            val = int(raw.strip())
        except ValueError as exc:
            raise ConfigurationError(
                f"Invalid {key}: '{raw}' is not a valid integer"
            ) from exc

    if min_value is not None and val < min_value:
        raise ConfigurationError(
            f"Invalid {key}: {val} must be >= {min_value}"
        )
    if max_value is not None and val > max_value:
        raise ConfigurationError(
            f"Invalid {key}: {val} must be <= {max_value}"
        )
    return val


def env_float(
    key: str,
    default: float,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
    env: Mapping[str, str] | None = None,
) -> float:
    source = env if env is not None else os.environ
    raw = source.get(key)
    if raw is None or not raw.strip():
        val = default
    else:
        try:
            val = float(raw.strip())
        except ValueError as exc:
            raise ConfigurationError(
                f"Invalid {key}: '{raw}' is not a valid number"
            ) from exc

    if min_value is not None and val < min_value:
        raise ConfigurationError(
            f"Invalid {key}: {val} must be >= {min_value}"
        )
    if max_value is not None and val > max_value:
        raise ConfigurationError(
            f"Invalid {key}: {val} must be <= {max_value}"
        )
    return val


def env_bool(
    key: str,
    default: bool,
    *,
    env: Mapping[str, str] | None = None,
) -> bool:
    source = env if env is not None else os.environ
    raw = source.get(key)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized in {"true", "1", "yes", "t"}:
        return True
    if normalized in {"false", "0", "no", "f"}:
        return False
    raise ConfigurationError(
        f"Invalid {key}: '{raw}' is not a valid boolean"
    )


def env_url(
    key: str,
    default: str,
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    source = env if env is not None else os.environ
    raw = source.get(key)
    if raw is None or not raw.strip():
        val = default
    else:
        val = raw.strip()

    parsed = urlparse(val)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigurationError(
            f"Invalid {key}: '{val}' is not a valid HTTP/HTTPS URL"
        )
    return val


class Settings:
    """Runtime configuration loaded and validated from environment variables."""

    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        source = env if env is not None else os.environ
        self.app_name: str = env_str("APP_NAME", "VeriCar", env=source)
        self.app_env: str = env_str("APP_ENV", "development", env=source)
        self.host: str = env_str("HOST", "127.0.0.1", env=source)
        self.port: int = env_int("PORT", 8000, min_value=1, max_value=65535, env=source)

        self.hindsight_base_url: str = env_url("HINDSIGHT_BASE_URL", "http://localhost:8888", env=source)
        self.hindsight_api_key: str = source.get("HINDSIGHT_API_KEY", "")
        self.hindsight_timeout: float = env_float("HINDSIGHT_TIMEOUT", 30.0, min_value=0.001, env=source)
        self.hindsight_startup_check: bool = env_bool("HINDSIGHT_STARTUP_CHECK", False, env=source)

        self.groq_base_url: str = env_url("GROQ_BASE_URL", "https://api.groq.com/openai/v1", env=source)
        self.groq_api_key: str = source.get("GROQ_API_KEY", "")
        self.groq_model: str = env_str("GROQ_MODEL", "llama-3.3-70b-versatile", env=source)
        self.groq_timeout: float = env_float("GROQ_TIMEOUT", 20.0, min_value=0.001, env=source)

        self.db_path: str = source.get("DB_PATH", "data/vericar.db")


settings = Settings()

"""Application settings, loaded from the project's .env file using python-dotenv.

`dotenv_values()` reads the .env file into a plain dict, e.g. {"API_PORT": "8000"}.
Every value in that dict is text, so numbers are converted with int() below.
Any key missing from .env falls back to the default given here.
"""

from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

# .../app  and the project root one level up (where .env lives)
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Absolute path, so .env is found whatever folder the server is started from.
# If .env does not exist this is simply an empty dict and all defaults apply.
_env: dict[str, str | None] = dotenv_values(ENV_FILE)


def _get(key: str, default: str) -> str:
    """Return the .env value for key, or the default if missing/blank."""
    value = _env.get(key)
    return value if value else default


def _get_int(key: str, default: int) -> int:
    """Like _get, but converts to int and fails with a clear message if invalid."""
    raw = _get(key, str(default))
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"Invalid value in {ENV_FILE.name}: {key}={raw!r} must be a whole number") from None


def _get_list(key: str) -> list[str]:
    """Comma-separated value -> list of trimmed, non-empty items."""
    return [item.strip() for item in _get(key, "").split(",") if item.strip()]


LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def _get_log_level(key: str, default: str) -> str:
    level = _get(key, default).upper()
    if level not in LOG_LEVELS:
        raise ValueError(f"Invalid value in {ENV_FILE.name}: {key}={level!r} must be one of {', '.join(LOG_LEVELS)}")
    return level


@dataclass(frozen=True)
class Settings:
    app_name: str
    data_dir: Path
    documents_dir: Path
    api_host: str
    api_port: int
    mcp_host: str
    mcp_port: int
    mcp_allowed_hosts: tuple[str, ...]
    max_results: int
    log_dir: Path
    log_level: str
    log_max_mb: int
    log_backup_count: int


settings = Settings(
    app_name=_get("APP_NAME", "AI Knowledge Server"),
    data_dir=Path(_get("DATA_DIR", str(APP_DIR / "data"))),
    documents_dir=Path(_get("DOCUMENTS_DIR", str(APP_DIR / "documents"))),
    api_host=_get("API_HOST", "127.0.0.1"),
    api_port=_get_int("API_PORT", 8000),
    mcp_host=_get("MCP_HOST", "127.0.0.1"),
    mcp_port=_get_int("MCP_PORT", 8001),
    mcp_allowed_hosts=tuple(_get_list("MCP_ALLOWED_HOSTS")),
    max_results=_get_int("MAX_RESULTS", 5),
    log_dir=Path(_get("LOG_DIR", str(PROJECT_ROOT / "logs"))),
    log_level=_get_log_level("LOG_LEVEL", "INFO"),
    log_max_mb=_get_int("LOG_MAX_MB", 5),
    log_backup_count=_get_int("LOG_BACKUP_COUNT", 5),
)

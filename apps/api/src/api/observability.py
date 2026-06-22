"""Centralised logging configuration.

Call ``configure_logging()`` once at process start (the API lifespan and the
CLI both do). Logs go to stderr; when ``LOG_DIR`` is set they are also written
to a rotating file. ``LOG_FORMAT=json`` emits structured one-line JSON records.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import UTC, datetime

from api.config import Settings, get_settings

_configured = False

_TEXT_FORMAT = "%(asctime)s %(levelname)s %(name)s · %(message)s"
_TIME_FORMAT = "%H:%M:%S"
# Third-party loggers that spam INFO (one line per HTTP request, etc.).
_NOISY = ("httpx", "httpcore", "openai", "urllib3", "asyncio")

_LEVEL_COLORS = {"DEBUG": "37", "INFO": "36", "WARNING": "33", "ERROR": "31", "CRITICAL": "41"}


def short_error(exc: BaseException) -> str:
    """One-line, human description of an exception for logs — no traceback. Maps
    the common provider failures to a clear phrase (rate limit, auth, timeout…)."""
    name = type(exc).__name__
    status = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None
    )
    if status == 429 or "RateLimit" in name:
        return "rate limited (429)"
    if status == 401 or "Authentication" in name:
        return "auth failed (401) — check the API key"
    if status == 403:
        return "forbidden (403)"
    if "Timeout" in name:
        return "timed out"
    if "Connection" in name:
        return "connection error"
    first = (str(exc).strip().splitlines() or [""])[0]
    return (f"{name}: {first}" if first else name)[:140]


class CleanFormatter(logging.Formatter):
    """Short console lines: `HH:MM:SS LEVEL name · message`, with the `api.`
    prefix stripped and the level coloured when writing to a terminal."""

    def __init__(self, *, color: bool) -> None:
        super().__init__(_TEXT_FORMAT, datefmt=_TIME_FORMAT)
        self._color = color

    def format(self, record: logging.LogRecord) -> str:
        record.name = record.name.removeprefix("api.")
        if self._color and (code := _LEVEL_COLORS.get(record.levelname)):
            record.levelname = f"\033[{code}m{record.levelname}\033[0m"
        return super().format(record)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _formatter(settings: Settings, *, color: bool) -> logging.Formatter:
    if settings.log_format == "json":
        return JsonFormatter()
    return CleanFormatter(color=color)


def configure_logging(settings: Settings | None = None, *, force: bool = False) -> None:
    """Idempotently configure the root logger from settings."""
    global _configured
    if _configured and not force:
        return
    settings = settings or get_settings()
    level = settings.log_level.upper()

    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console = logging.StreamHandler()
    console.setFormatter(_formatter(settings, color=sys.stderr.isatty()))
    root.addHandler(console)

    if settings.log_dir:
        os.makedirs(settings.log_dir, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(settings.log_dir, "api.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(_formatter(settings, color=False))  # no ANSI in files
        root.addHandler(file_handler)

    # Quiet third-party loggers that would otherwise drown out app logs.
    for name in _NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)

    # Let uvicorn/sqlalchemy propagate to the root handlers instead of their own.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True

    _configured = True

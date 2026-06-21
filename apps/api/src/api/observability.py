"""Centralised logging configuration.

Call ``configure_logging()`` once at process start (the API lifespan and the
CLI both do). Logs go to stderr; when ``LOG_DIR`` is set they are also written
to a rotating file. ``LOG_FORMAT=json`` emits structured one-line JSON records.
"""

import json
import logging
import logging.handlers
import os
from datetime import UTC, datetime

from api.config import Settings, get_settings

_configured = False

_TEXT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


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


def _formatter(settings: Settings) -> logging.Formatter:
    if settings.log_format == "json":
        return JsonFormatter()
    return logging.Formatter(_TEXT_FORMAT)


def configure_logging(settings: Settings | None = None, *, force: bool = False) -> None:
    """Idempotently configure the root logger from settings."""
    global _configured
    if _configured and not force:
        return
    settings = settings or get_settings()
    formatter = _formatter(settings)
    level = settings.log_level.upper()

    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    if settings.log_dir:
        os.makedirs(settings.log_dir, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(settings.log_dir, "api.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    # Let uvicorn/sqlalchemy propagate to the root handlers instead of their own.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True

    _configured = True

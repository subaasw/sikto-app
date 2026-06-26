"""The one logging module. Built on loguru; reused everywhere via `get_logger`.

    from api.logger import get_logger
    log = get_logger("worker")   # lines render as [worker] ...

Call `configure_logging()` once at process start (the API lifespan and the CLI
both do). Console lines read:

    [api]    INFO    12:04:31  200 GET  /lessons/abc   23ms  ·a1b2c3d4

The whole line is colored by level, so 4xx (warning) and 5xx (error) stand out.
Request lines come from `add_request_logging`; unhandled errors are turned into
a clean `{error, request_id}` 500 by `register_exception_handlers`, with the id
echoed on the access line and an `X-Request-ID` header so a user error maps to
exact logs.
"""

import logging
import os
import sys
from collections.abc import Awaitable, Callable
from types import FrameType
from typing import TYPE_CHECKING
from uuid import uuid4

from loguru import logger

from api.config import Settings, get_settings

if TYPE_CHECKING:
    from fastapi import FastAPI, Request, Response
    from loguru import Logger, Record

_configured = False
_NOISY = ("httpx", "httpcore", "openai", "urllib3", "asyncio")
_MAX_PATH = 60


def get_logger(component: str = "api") -> "Logger":
    return logger.bind(component=component)


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


# Badge colors: (foreground, background). loguru markup uses lowercase tags for
# foreground and UPPERCASE for background, e.g. <white><RED> → white on red.
_LEVEL_BG = {
    "TRACE": ("white", "black"),
    "DEBUG": ("white", "black"),
    "INFO": ("white", "blue"),
    "SUCCESS": ("white", "green"),
    "WARNING": ("black", "yellow"),
    "ERROR": ("white", "red"),
    "CRITICAL": ("white", "red"),
}
# Keyed by status-code class (2xx, 3xx, ...).
_STATUS_BG = {2: ("white", "green"), 3: ("black", "cyan"), 4: ("black", "yellow"), 5: ("white", "red")}


def _badge(text: str, fg: str, bg: str) -> str:
    """A bold, space-padded block: ` text ` as colored fg on a colored bg."""
    BG = bg.upper()
    return f"<{fg}><{BG}><bold> {text} </bold></{BG}></{fg}>"


def _format(record: "Record", *, component: bool = True) -> str:
    """Build the format string per record so the request-id suffix only shows
    inside a request. Field *values* (e.g. the path in {message}) aren't parsed
    for markup by loguru, so user input can't inject color tags — the level and
    status we inline below are our own controlled values.

    ``component=False`` drops the ``[api]`` tag for the console sink — the dev
    process runner already prefixes each line with the process name, so it'd be
    a duplicate. The file sink keeps the tag (no runner prefix there)."""
    extra = record["extra"]
    extra.setdefault("component", "api")
    lvl = record["level"].name
    fg, bg = _LEVEL_BG.get(lvl, ("white", "blue"))

    line = "<dim>[{extra[component]}]</dim> " if component else ""
    line += _badge(f"{lvl:<7}", fg, bg) + " <dim>→</dim>  "
    line += "<green>{time:HH:mm:ss}</green>  "
    if "status" in extra:
        sfg, sbg = _STATUS_BG.get(int(extra["status"]) // 100, ("white", "red"))
        line += _badge(str(extra["status"]), sfg, sbg) + " "
    line += "<level>{message}</level>"
    if "request_id" in extra:
        line += "  <dim>·{extra[request_id]}</dim>"
    return line + "\n"


def _console_format(record: "Record") -> str:
    return _format(record, component=False)


def configure_logging(settings: Settings | None = None, *, force: bool = False) -> None:
    """Idempotently route all logging through loguru with our format."""
    global _configured
    if _configured and not force:
        return
    settings = settings or get_settings()
    level = settings.log_level.upper()
    as_json = settings.log_format == "json"

    logger.configure(extra={"component": "api"})
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format=_console_format,
        serialize=as_json,
        backtrace=True,
        diagnose=False,  # never dump local variable values (could leak secrets)
    )
    if settings.log_dir:
        os.makedirs(settings.log_dir, exist_ok=True)
        logger.add(
            os.path.join(settings.log_dir, "api.log"),
            level=level,
            format=_format,
            serialize=as_json,
            colorize=False,  # no ANSI in files
            rotation="10 MB",
            retention=5,
            backtrace=True,
            diagnose=False,
        )

    # Route stdlib logging (incl. uvicorn/sqlalchemy) into loguru.
    logging.root.handlers = [_InterceptHandler()]
    logging.root.setLevel(level)
    for name in _NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)
    for name in ("uvicorn", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
    # Our middleware (add_request_logging) already emits one clean access line per
    # request; uvicorn.access would duplicate it in raw form, so silence it.
    logging.getLogger("uvicorn.access").disabled = True

    _configured = True


def _component_for(name: str) -> str:
    if "worker" in name:
        return "worker"
    if name.startswith(("sqlalchemy", "asyncpg")):
        return "db"
    return "api"


class _InterceptHandler(logging.Handler):
    """Standard loguru recipe: redirect stdlib records into loguru, preserving
    level, call-site depth, and exception info; tag the component by logger name."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            lvl: str | int = logger.level(record.levelname).name
        except ValueError:
            lvl = record.levelno
        frame: FrameType | None = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.bind(component=_component_for(record.name)).opt(
            depth=depth, exception=record.exc_info
        ).log(lvl, record.getMessage())


# --- request logging + exception handling (FastAPI wiring) -----------------

def _truncate(path: str) -> str:
    return path if len(path) <= _MAX_PATH else path[: _MAX_PATH - 1] + "…"


def _access_level(status: int, path: str) -> str:
    if status >= 500:
        return "ERROR"
    if status >= 400:
        return "WARNING"
    if path in ("/health", "/"):  # health checks shouldn't flood INFO
        return "DEBUG"
    return "INFO"


def add_request_logging(app: "FastAPI") -> None:
    @app.middleware("http")
    async def _log_requests(
        request: "Request",
        call_next: "Callable[[Request], Awaitable[Response]]",
    ) -> "Response":
        import time

        rid = uuid4().hex[:8]
        request.state.request_id = rid
        start = time.perf_counter()
        with logger.contextualize(request_id=rid):
            try:
                response = await call_next(request)
            except Exception:
                dur = (time.perf_counter() - start) * 1000
                logger.bind(component="api", status=500).opt(exception=True).error(
                    f"{request.method:<4} {_truncate(request.url.path)}  {dur:.0f}ms"
                )
                raise  # let the exception handler build the response
            dur = (time.perf_counter() - start) * 1000
            msg = f"{request.method:<4} {_truncate(request.url.path)}  {dur:.0f}ms"
            logger.bind(component="api", status=response.status_code).log(
                _access_level(response.status_code, request.url.path), msg
            )
            response.headers["X-Request-ID"] = rid
            return response


def register_exception_handlers(app: "FastAPI") -> None:
    from fastapi.responses import JSONResponse

    @app.exception_handler(Exception)
    async def _unhandled(request: "Request", exc: Exception) -> JSONResponse:
        # The middleware already logged the traceback under this request id.
        rid = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=500,
            content={"error": "internal error", "request_id": rid},
            headers={"X-Request-ID": rid} if rid else None,
        )


def demo() -> None:
    configure_logging(force=True)
    get_logger("api").info("plain api line")
    get_logger("worker").info("rendered lesson abc")
    with logger.contextualize(request_id="a1b2c3d4"):
        logger.bind(component="api", status=200).info("GET  /lessons/abc   23ms")
        logger.bind(component="api", status=404).warning("GET  /media/missing.png   2ms")
        logger.bind(component="api", status=500).error("POST /lessons   12ms")
    assert _component_for("api.jobs.worker") == "worker"
    assert _component_for("sqlalchemy.engine") == "db"
    assert _access_level(500, "/x") == "ERROR"
    assert _access_level(404, "/x") == "WARNING"
    assert _access_level(200, "/health") == "DEBUG"
    assert _truncate("/" + "a" * 80).endswith("…")
    print("ok")


if __name__ == "__main__":
    demo()

"""Logging module: component tags, access-line shape, and the clean-500 +
request-id correlation contract."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from loguru import logger

from api.logger import (
    _access_level,
    add_request_logging,
    get_logger,
    register_exception_handlers,
)


def _capture() -> list[dict]:
    records: list[dict] = []
    logger.remove()
    logger.add(lambda m: records.append(m.record), level="DEBUG")
    return records


def test_component_is_bound() -> None:
    records = _capture()
    get_logger("worker").info("hi")
    assert records[-1]["extra"]["component"] == "worker"
    assert get_logger().info  # default component callable


def test_access_level_mapping() -> None:
    assert _access_level(200, "/lessons") == "INFO"
    assert _access_level(200, "/health") == "DEBUG"  # health checks quieted
    assert _access_level(404, "/x") == "WARNING"
    assert _access_level(500, "/x") == "ERROR"


def _app() -> FastAPI:
    app = FastAPI()
    add_request_logging(app)
    register_exception_handlers(app)

    @app.get("/ok")
    def ok() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/boom")
    def boom() -> None:
        raise ValueError("kaboom")

    return app


def test_request_id_header_on_success() -> None:
    client = TestClient(_app())
    r = client.get("/ok")
    assert r.status_code == 200
    assert len(r.headers["X-Request-ID"]) == 8


def test_unhandled_error_is_clean_500_with_matching_request_id() -> None:
    client = TestClient(_app(), raise_server_exceptions=False)
    r = client.get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["error"] == "internal error"
    assert body["request_id"] == r.headers["X-Request-ID"]  # body ↔ header correlate

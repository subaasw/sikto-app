"""Single exception handler mapping any AuthError to a JSON HTTP response."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .errors import AuthError


def register_auth_error_handler(app: FastAPI) -> None:
    @app.exception_handler(AuthError)
    async def _handle(_: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

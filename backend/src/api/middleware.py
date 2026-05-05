"""API middleware — X-API-Key 鉴权 + CORS"""

from __future__ import annotations

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import get_settings

settings = get_settings()

SKIP_AUTH_PATHS = {"/docs", "/openapi.json", "/redoc", "/health"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in SKIP_AUTH_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
        if not api_key or api_key != settings.xhs_api_key:
            return Response(
                content='{"success":false,"error":"invalid or missing x-api-key"}',
                status_code=401,
                media_type="application/json",
            )
        return await call_next(request)


def setup_cors(app) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

"""Application authentication gateway.

Production accepts either the service API key (machine-to-machine) or a valid
short-lived advisor bearer session. Development intentionally remains open for
local smoke tests.
"""
import hmac
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings
from src.shared.auth import get_current_advisor

UNPROTECTED_ROUTES = {"/", "/docs", "/redoc", "/openapi.json", "/api/v1/health", "/api/v1/health/readiness", "/api/v1/health/dependencies"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in UNPROTECTED_ROUTES or request.url.path.startswith("/api/v1/webhooks/"):
            return await call_next(request)

        if settings.ENV == "development" and settings.AUTH_MODE == "api_key":
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if api_key and hmac.compare_digest(api_key, settings.API_KEY):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer ") and get_current_advisor(auth[7:].strip()):
            return await call_next(request)

        if not api_key and not auth:
            return JSONResponse(status_code=401, content={"detail": "Authentication required."})
        return JSONResponse(status_code=403, content={"detail": "Invalid API key or session."})

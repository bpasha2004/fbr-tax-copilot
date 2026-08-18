"""Security hardening middleware: distributed rate limits, payload limits, headers and request telemetry."""
import json
import re
import time
import hashlib
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import settings
from api.middleware.ratelimit import check_rate_limit, RATE_LIMIT_WINDOW
from observability.events import request_id, emit, Timer

MAX_PAYLOAD_BYTES = settings.MAX_PAYLOAD_BYTES
_XSS_PATTERNS = re.compile(r"(<\s*script|javascript\s*:|on\w+\s*=|<\s*iframe|<\s*object|<\s*embed|expression\s*\(|vbscript\s*:|data\s*:\s*text/html)", re.IGNORECASE)
_SKIP_SCAN_PREFIXES = {"/docs", "/redoc", "/openapi.json", "/favicon.ico"}


def _suspicious(value: str) -> bool:
    return bool(_XSS_PATTERNS.search(value))


def _scan_dict(data, depth: int = 0) -> bool:
    if depth > 8:
        return False
    if isinstance(data, str):
        return _suspicious(data)
    if isinstance(data, dict):
        return any(_scan_dict(v, depth + 1) for v in data.values())
    if isinstance(data, (list, tuple)):
        return any(_scan_dict(v, depth + 1) for v in data)
    return False


def _get_client_ip(request: Request) -> str:
    if settings.TRUST_PROXY_HEADERS:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Cache-Control": "no-store",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin"
}


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rid = request.headers.get("X-Request-ID") or request_id()
        timer = Timer()
        credential = request.headers.get("Authorization") or request.headers.get("X-API-Key") or ""
        identity = "auth:" + hashlib.sha256(credential.encode()).hexdigest()[:16] if credential else f"ip:{_get_client_ip(request)}"
        limited = check_rate_limit(identity, fail_closed=(settings.ENV == "production"))
        if limited is None or limited is False:
            if settings.ENV == "production" and limited is None:
                return JSONResponse(status_code=503, content={"detail": "Rate limiting service unavailable."}, headers={"X-Request-ID": rid})
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Slow down.", "retry_after": RATE_LIMIT_WINDOW},
                headers={"Retry-After": str(RATE_LIMIT_WINDOW), "X-Request-ID": rid},
            )

        content_length = request.headers.get("content-length")
        try:
            if content_length and int(content_length) > MAX_PAYLOAD_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Payload too large."}, headers={"X-Request-ID": rid})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length."}, headers={"X-Request-ID": rid})

        raw_query = str(request.url.query)
        if raw_query and _suspicious(raw_query):
            return JSONResponse(status_code=400, content={"detail": "Unsafe markup detected in query parameters."}, headers={"X-Request-ID": rid})

        path = request.url.path
        if not any(path.startswith(p) for p in _SKIP_SCAN_PREFIXES) and request.method in {"POST", "PUT", "PATCH"}:
            ct = request.headers.get("content-type", "")
            if "application/json" in ct:
                try:
                    body = await request.body()
                    if len(body) > MAX_PAYLOAD_BYTES:
                        return JSONResponse(status_code=413, content={"detail": "Request body too large."}, headers={"X-Request-ID": rid})
                    data = json.loads(body) if body else {}
                    if _scan_dict(data):
                        return JSONResponse(status_code=400, content={"detail": "Unsafe markup detected in request body."}, headers={"X-Request-ID": rid})
                except json.JSONDecodeError:
                    pass

        response = await call_next(request)
        emit("http_request", request_id=rid, method=request.method, path=path, status_code=response.status_code, latency_ms=timer.ms())
        for k, v in _SECURITY_HEADERS.items():
            response.headers[k] = v
        response.headers["X-Request-ID"] = rid
        if settings.ENV == "production":
            response.headers["Content-Security-Policy"] = "default-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
        return response

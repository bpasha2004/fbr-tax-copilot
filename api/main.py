import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routes.health import router as health_router
from api.routes.tax import router as tax_router
from api.routes.clients import router as clients_router
from api.routes.auth import router as auth_router
from api.routes.rag import router as rag_router
from api.routes.audit import router as audit_router
from api.routes.payments import router as payments_router
from api.middleware.auth import APIKeyMiddleware
from api.middleware.security import SecurityMiddleware
from api.middleware.hmac_webhook import router as webhooks_router
from config.settings import settings
from src.shared.models import init_db
from observability.metrics import inc, observe


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="FBR Tax Copilot — B2B Advisory Platform",
    description=(
        "AI-powered FBR tax compliance copilot for Pakistani Tax Advisors. "
        "Covers: salaried (Division I), business (Division II), freelance (Section 154A). "
        "Outputs: IRIS 2.0 portal entries, document checklists, legal citations."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware stack — order matters (last added = first executed)
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENV == "development" else cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "X-API-Key",
        "Content-Type",
        "X-Request-ID",
        "X-Webhook-Signature",
        "X-Webhook-Timestamp",
        "Idempotency-Key",
    ],
)
app.add_middleware(SecurityMiddleware)   # sanitization + rate limiting + headers
app.add_middleware(APIKeyMiddleware)

app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(tax_router)
app.include_router(clients_router)
app.include_router(auth_router)
app.include_router(webhooks_router)
app.include_router(rag_router)
app.include_router(audit_router)
app.include_router(payments_router)


# ── Global error handling ───────────────────────────────────────────────────
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    print(f"[unhandled] {request.method} {request.url.path}: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again or contact support."},
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    favicon_svg = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<rect width="100" height="100" rx="24" ry="24" fill="#3B82F6"/>'
        '<text x="50" y="62" text-anchor="middle" font-family="Arial, sans-serif" '
        'font-size="58" font-weight="700" fill="#FFFFFF">F</text>'
        '</svg>'
    )
    return Response(content=favicon_svg, media_type="image/svg+xml")


# ── SPA Frontend Mounting ───────────────────────────────────────────────────
frontend_base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
possible_dists = [
    os.path.join(frontend_base, ".output", "public"),
    os.path.join(frontend_base, "dist"),
    os.path.join(frontend_base, "build"),
    os.path.join(frontend_base, "public"),
]

frontend_dist = next((d for d in possible_dists if os.path.exists(d)), possible_dists[0])

if os.path.exists(os.path.join(frontend_dist, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")


@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = ""):
    """Serve the Lovable React single-page application (SPA) or fallback dashboard page."""
    if full_path:
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)

    for dist in possible_dists:
        index_path = os.path.join(dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)

    # Fallback dashboard HTML when frontend has not been compiled (e.g. test / dev environments)
    fallback_dashboard = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>FBR Tax Copilot Dashboard</title>
</head>
<body>
    <h1>FBR Tax Copilot — B2B Advisory Platform</h1>
    <p>Status: <strong>Online</strong></p>
    <p>Documentation: <a href="/docs">Swagger UI (/docs)</a> | <a href="/redoc">ReDoc (/redoc)</a></p>
</body>
</html>"""
    return HTMLResponse(content=fallback_dashboard, status_code=200)
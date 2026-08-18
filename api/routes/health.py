from fastapi import APIRouter
from config.settings import settings
from datetime import datetime, timezone
from fastapi.responses import PlainTextResponse, JSONResponse

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "FBR Tax Platform",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
    }


@router.get("/health/readiness")
def readiness_check():
    """Fail readiness if core persistence or vector retrieval is unavailable."""
    from config.settings import settings
    checks = {"database": False, "chromadb": False, "redis": False}
    try:
        from src.shared.models import get_engine
        with get_engine().connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        checks["database"] = True
    except Exception:
        pass
    try:
        from rag.vector_store import ChromaVectorStore
        ChromaVectorStore().count()
        checks["chromadb"] = True
    except Exception:
        pass
    try:
        import redis
        r = redis.Redis.from_url(settings.REDIS_URL)
        checks["redis"] = bool(r.ping())
    except Exception:
        pass
    status = "ready" if all(checks.values()) else "degraded"
    return JSONResponse(status_code=200 if status == "ready" else 503, content={"status": status, "checks": checks})


@router.get("/health/dependencies")
def dependency_health():
    """Report live dependency status without failing the basic liveness probe."""
    import httpx
    from config.settings import settings
    result = {"api": "ok", "database": "offline", "redis": "offline", "chromadb": "offline", "ollama": "offline", "ollama_model": settings.OLLAMA_MODEL}
    try:
        from src.shared.models import get_engine
        with get_engine().connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        result["database"] = "ok"
    except Exception as exc:
        result["database_error"] = type(exc).__name__
    try:
        import redis
        result["redis"] = "ok" if redis.Redis.from_url(settings.REDIS_URL).ping() else "offline"
    except Exception as exc:
        result["redis_error"] = type(exc).__name__
    try:
        from rag.vector_store import ChromaVectorStore
        result["chromadb"] = f"ok:{ChromaVectorStore().count()} chunks"
    except Exception as exc:
        result["chromadb_error"] = type(exc).__name__
    try:
        r = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=3.0)
        result["ollama"] = "ok" if r.status_code < 400 else f"http_{r.status_code}"
        if r.is_success:
            names = {m.get("name") for m in r.json().get("models", [])}
            result["ollama_model_loaded"] = settings.OLLAMA_MODEL in names or f"{settings.OLLAMA_MODEL}:latest" in names
    except Exception as exc:
        result["ollama_error"] = type(exc).__name__
    return result


@router.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
def metrics():
    from observability.metrics import prometheus_text
    return prometheus_text()

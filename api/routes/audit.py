from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import select

from src.shared.auth import get_current_advisor, require_role
from src.shared.models import audit_events, get_engine

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


def _actor(auth: str | None):
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    advisor = get_current_advisor(auth[7:].strip())
    if not advisor:
        raise HTTPException(status_code=401, detail="Session expired or invalid.")
    return require_role(advisor, "admin", "auditor")


@router.get("")
def list_audit_events(limit: int = Query(100, ge=1, le=500), authorization: str | None = Header(None)):
    actor = _actor(authorization)
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(audit_events).order_by(audit_events.c.id.desc()).limit(limit)
        ).mappings().all()
    return {"viewer": actor["role"], "events": [dict(r) for r in rows]}

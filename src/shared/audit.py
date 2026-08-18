"""Tamper-evident application audit trail with sensitive-field sanitization."""
from datetime import datetime, timezone
import hashlib, json
from sqlalchemy import insert, select
from src.shared.models import get_engine, audit_events
from observability.events import sanitize


def record_audit(*, actor_id=None, action: str, resource_type: str, resource_id=None,
                 request_id: str | None = None, ip_address: str | None = None,
                 metadata: dict | None = None) -> int | None:
    safe = sanitize(metadata or {})
    created = datetime.now(timezone.utc)
    with get_engine().begin() as conn:
        previous = conn.execute(select(audit_events.c.event_hash).order_by(audit_events.c.id.desc()).limit(1)).scalar_one_or_none()
        canonical = {
            "actor_id": actor_id, "action": action, "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id is not None else None,
            "request_id": request_id, "ip_address": ip_address, "metadata": safe,
            "created_at": created.isoformat(), "prev_hash": previous,
        }
        event_hash = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        result = conn.execute(insert(audit_events).values(**canonical, event_hash=event_hash))
        return result.inserted_primary_key[0] if result.inserted_primary_key else None

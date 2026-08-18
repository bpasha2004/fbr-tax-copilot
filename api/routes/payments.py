"""Payment lifecycle endpoints: refunds, chargebacks and reconciliation."""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from decimal import Decimal
from src.shared.auth import get_current_advisor, require_role, require_write_access
from src.shared.payment_service import request_refund, mark_refunded, open_chargeback, resolve_chargeback, reconcile
from src.shared.models import get_engine, payments
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

def actor(auth: str | None):
    if not auth or not auth.startswith("Bearer "): raise HTTPException(401, "Missing Authorization header.")
    advisor = get_current_advisor(auth[7:].strip())
    if not advisor: raise HTTPException(401, "Session expired or invalid.")
    return advisor

class RefundRequest(BaseModel):
    payment_id: int
    amount_pkr: Decimal | None = Field(None, gt=0)

class ReconcileRequest(BaseModel):
    provider: str = Field(..., min_length=2, max_length=32)
    records: list[dict] = Field(default_factory=list, max_length=5000)

class ChargebackRequest(BaseModel):
    payment_id: int
    payload: dict = Field(default_factory=dict)

class ChargebackResolution(BaseModel):
    outcome: str = Field(..., pattern="^(won|lost)$")


def _owned_payment(advisor: dict, payment_id: int) -> dict:
    with get_engine().connect() as conn:
        row = conn.execute(select(payments).where(payments.c.id == payment_id)).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Payment not found.")
    if advisor.get("role") not in {"admin", "auditor", "reviewer"} and row["advisor_id"] != advisor["advisor_id"]:
        raise HTTPException(status_code=404, detail="Payment not found.")
    return dict(row)

@router.post("/{payment_id}/refund")
def refund(payment_id: int, body: RefundRequest, authorization: str | None = Header(None)):
    advisor = require_write_access(actor(authorization))
    if body.payment_id != payment_id: raise HTTPException(422, "payment_id does not match URL.")
    _owned_payment(advisor, payment_id)
    try: return request_refund(payment_id, body.amount_pkr)
    except ValueError as exc: raise HTTPException(409, str(exc))

@router.post("/{payment_id}/refund/complete")
def refund_complete(payment_id: int, authorization: str | None = Header(None)):
    advisor = require_write_access(actor(authorization))
    _owned_payment(advisor, payment_id)
    try: return mark_refunded(payment_id, {"source": "provider_confirmation"})
    except ValueError as exc: raise HTTPException(409, str(exc))

@router.post("/{payment_id}/chargeback")
def chargeback(payment_id: int, body: ChargebackRequest, authorization: str | None = Header(None)):
    advisor = require_write_access(actor(authorization))
    require_role(advisor, "admin", "reviewer")
    _owned_payment(advisor, payment_id)
    if body.payment_id != payment_id: raise HTTPException(422, "payment_id does not match URL.")
    try: return open_chargeback(payment_id, body.payload)
    except ValueError as exc: raise HTTPException(409, str(exc))

@router.post("/{payment_id}/chargeback/resolve")
def resolve(payment_id: int, body: ChargebackResolution, authorization: str | None = Header(None)):
    advisor = require_write_access(actor(authorization))
    require_role(advisor, "admin", "reviewer")
    _owned_payment(advisor, payment_id)
    try: return resolve_chargeback(payment_id, body.outcome)
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc))

@router.post("/reconcile")
def reconciliation(body: ReconcileRequest, authorization: str | None = Header(None)):
    require_role(actor(authorization), "admin", "reviewer", "auditor")
    return reconcile(body.provider, body.records)

@router.get("/{payment_id}")
def payment_status(payment_id: int, authorization: str | None = Header(None)):
    advisor = actor(authorization)
    with get_engine().connect() as conn:
        row = conn.execute(select(payments).where(payments.c.id == payment_id)).mappings().first()
    if not row: raise HTTPException(404, "Payment not found.")
    if row["advisor_id"] != advisor["advisor_id"] and advisor["role"] not in {"admin", "auditor", "reviewer"}:
        raise HTTPException(404, "Payment not found.")
    return dict(row)

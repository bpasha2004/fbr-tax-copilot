"""
Client Management Routes — Multi-Tenant Agency Dashboard
Advisor-scoped CRUD for client profiles and calculation history.
Auth: session token from Authorization header (Bearer).
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, Literal
from math import isfinite
import secrets

from src.shared.auth import get_current_advisor, require_write_access
from src.shared.dashboard import AdvisorDashboard
from src.shared.payments import PaymentRouter
from src.shared.models import init_db
from src.shared.payment_service import create_payment
from src.shared.audit import record_audit

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])


def _require_advisor(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    token   = authorization.removeprefix("Bearer ").strip()
    advisor = get_current_advisor(token)
    if not advisor:
        raise HTTPException(status_code=401, detail="Session expired or invalid.")
    return advisor


# ── Schemas ───────────────────────────────────────────────────────────────────

class ClientCreate(BaseModel):
    full_name:      str             = Field(..., examples=["Ali Hassan"])
    taxpayer_type:  Literal["salaried", "business", "freelance"] = Field("salaried")
    tax_year:       Literal["2025-26", "2026-27"] = Field("2026-27")
    cnic:           Optional[str]   = None
    ntn:            Optional[str]   = None
    email:          Optional[str]   = None
    phone:          Optional[str]   = None
    annual_income:  Optional[float] = Field(None, ge=0, le=1_000_000_000)
    notes:          Optional[str]   = None


class ClientUpdate(BaseModel):
    full_name:      Optional[str]   = None
    taxpayer_type:  Optional[Literal["salaried", "business", "freelance"]] = None
    tax_year:       Optional[Literal["2025-26", "2026-27"]] = None
    cnic:           Optional[str]   = None
    ntn:            Optional[str]   = None
    email:          Optional[str]   = None
    phone:          Optional[str]   = None
    annual_income:  Optional[float] = Field(None, ge=0, le=1_000_000_000)
    notes:          Optional[str]   = None


class SaveCalculationRequest(BaseModel):
    client_id:      int
    calc_result:    dict


class PaymentRouteRequest(BaseModel):
    amount_pkr:     float = Field(..., gt=0, le=10_000_000)
    client_type:    Literal["individual", "firm"] = Field("individual")
    reference:      Optional[str] = Field(None, max_length=128)
    preferred:      Optional[str] = None
    client_id:      Optional[int] = Field(None, gt=0)
    idempotency_key: str = Field(..., min_length=8, max_length=128)


# ── Dashboard summary ──────────────────────────────────────────────────────────

@router.get("/dashboard")
def get_dashboard(authorization: str = Header(None)):
    """Returns full agency dashboard: all clients, summary stats."""
    advisor = _require_advisor(authorization)
    db      = AdvisorDashboard(advisor_id=advisor["advisor_id"])
    return db.get_dashboard_summary()


# ── Client CRUD ───────────────────────────────────────────────────────────────

@router.get("")
def list_clients(authorization: str = Header(None)):
    """List all active clients for the authenticated advisor."""
    advisor = _require_advisor(authorization)
    db      = AdvisorDashboard(advisor_id=advisor["advisor_id"])
    return {"clients": db.list_clients()}


@router.post("")
def create_client(body: ClientCreate, authorization: str = Header(None)):
    """Create a new client profile."""
    advisor    = require_write_access(_require_advisor(authorization))
    db         = AdvisorDashboard(advisor_id=advisor["advisor_id"])
    client_id  = db.create_client(**body.model_dump())
    record_audit(actor_id=advisor["advisor_id"], action="client.create", resource_type="client", resource_id=client_id)
    return {"client_id": client_id, "status": "created"}


@router.get("/{client_id}")
def get_client(client_id: int, authorization: str = Header(None)):
    """Get a single client (advisor must own the client)."""
    advisor = _require_advisor(authorization)
    db      = AdvisorDashboard(advisor_id=advisor["advisor_id"])
    client  = db.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    return client


@router.patch("/{client_id}")
def update_client(client_id: int, body: ClientUpdate, authorization: str = Header(None)):
    """Update client fields."""
    advisor = require_write_access(_require_advisor(authorization))
    db      = AdvisorDashboard(advisor_id=advisor["advisor_id"])
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not db.update_client(client_id, **updates):
        raise HTTPException(status_code=404, detail="Client not found.")
    record_audit(actor_id=advisor["advisor_id"], action="client.update", resource_type="client", resource_id=client_id, metadata={"fields": sorted(updates)})
    return {"status": "updated"}


@router.delete("/{client_id}")
def deactivate_client(client_id: int, authorization: str = Header(None)):
    """Soft-delete: marks client inactive."""
    advisor = require_write_access(_require_advisor(authorization))
    db      = AdvisorDashboard(advisor_id=advisor["advisor_id"])
    if not db.deactivate_client(client_id):
        raise HTTPException(status_code=404, detail="Client not found.")
    record_audit(actor_id=advisor["advisor_id"], action="client.deactivate", resource_type="client", resource_id=client_id)
    return {"status": "deactivated"}


# ── Calculation history ───────────────────────────────────────────────────────

@router.post("/calculations/save")
def save_calculation(body: SaveCalculationRequest, authorization: str = Header(None)):
    """Persist a tax calculation result linked to a client."""
    advisor = require_write_access(_require_advisor(authorization))
    db      = AdvisorDashboard(advisor_id=advisor["advisor_id"])
    client = db.get_client(body.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    result = body.calc_result
    required = {"taxpayer_type", "tax_year", "annual_income", "tax_payable"}
    if not required.issubset(result):
        raise HTTPException(status_code=422, detail="calc_result is missing required tax fields.")
    if result.get("taxpayer_type") != client.get("taxpayer_type") or result.get("tax_year") != client.get("tax_year"):
        raise HTTPException(status_code=422, detail="Calculation taxpayer type and tax year must match the client profile.")
    for key in ("annual_income", "tax_payable", "effective_rate"):
        if result.get(key) is not None:
            try:
                if not isfinite(float(result[key])):
                    raise ValueError
            except (TypeError, ValueError):
                raise HTTPException(status_code=422, detail=f"{key} must be finite.")
    if float(result.get("tax_payable", 0)) < 0:
        raise HTTPException(status_code=422, detail="tax_payable cannot be negative.")
    try:
        calc_id = db.save_calculation(body.client_id, result)
        record_audit(actor_id=advisor["advisor_id"], action="calculation.save", resource_type="tax_calculation", resource_id=calc_id)
        return {"calculation_id": calc_id, "status": "saved"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/{client_id}/history")
def get_client_history(client_id: int, authorization: str = Header(None)):
    """Get calculation history for a client."""
    advisor = _require_advisor(authorization)
    db      = AdvisorDashboard(advisor_id=advisor["advisor_id"])
    return {"history": db.get_client_history(client_id)}


# ── Payment routing ───────────────────────────────────────────────────────────

@router.post("/payment/routes")
def get_payment_routes(body: PaymentRouteRequest, authorization: str = Header(None)):
    """
    Returns applicable payment routes for advisory fee collection.
    Individual clients → JazzCash / EasyPaisa.
    Firm/business clients → Raast IBFT / Bank Transfer.
    """
    advisor = require_write_access(_require_advisor(authorization))
    if not isfinite(body.amount_pkr):
        raise HTTPException(status_code=422, detail="amount_pkr must be finite.")
    if body.client_id is not None:
        owner = AdvisorDashboard(advisor_id=advisor["advisor_id"]).get_client(body.client_id)
        if not owner:
            raise HTTPException(status_code=404, detail="Client not found.")
    reference = (body.reference or "").strip() or f"FBR-{secrets.token_hex(8).upper()}"
    router_svc = PaymentRouter()
    routes = router_svc.route(
        amount_pkr=body.amount_pkr,
        client_type=body.client_type,
        reference=reference,
        preferred_method=body.preferred,
    )
    if not routes:
        raise HTTPException(
            status_code=503,
            detail="No payment destination is configured for the requested route.",
        )

    provider = routes[0].method
    try:
        payment = create_payment(
            advisor_id=advisor["advisor_id"], client_id=body.client_id, amount_pkr=body.amount_pkr,
            method=routes[0].method, provider=provider, reference=reference, idempotency_key=body.idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    record_audit(actor_id=advisor["advisor_id"], action="payment.create", resource_type="payment", resource_id=payment["id"], metadata={"amount_pkr": body.amount_pkr, "method": routes[0].method, "provider": provider})

    return {
        "payment_id": payment["id"],
        "payment_status": payment["status"],
        "payment_routes": router_svc.to_dict(routes),
        "note": "This creates a payment instruction only. Settlement is confirmed by a verified provider/bank notification or manual reconciliation.",
    }

"""Payment lifecycle, idempotency, settlement, refund, chargeback and reconciliation engine.

Provider adapters are deliberately separate: this module never invents a provider
API contract. A live adapter is enabled only when its official endpoint/credentials
are supplied through configuration.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib, json, uuid
from sqlalchemy import select, insert, update
from src.shared.models import get_engine, payments, payment_events, audit_reconciliation

PAYMENT_STATES = {"created", "pending", "succeeded", "failed", "expired", "refunded", "chargeback"}
ALLOWED_TRANSITIONS = {
    "created": {"pending", "succeeded", "failed", "expired"},
    "pending": {"succeeded", "failed", "expired"},
    "succeeded": {"refunded", "chargeback"},
    "failed": set(), "expired": set(), "refunded": set(), "chargeback": {"succeeded"},
}


def _now(): return datetime.now(timezone.utc)


def _event_id(payload: dict, raw_body: bytes = b"") -> str:
    explicit = payload.get("event_id") or payload.get("id") or payload.get("transactionId")
    if explicit: return str(explicit)
    return hashlib.sha256(raw_body).hexdigest()


def _find_payment(conn, provider: str, reference: str):
    return conn.execute(select(payments).where(payments.c.provider == provider, payments.c.reference == reference)).mappings().first()


def create_payment(*, advisor_id: int, amount_pkr: Decimal, method: str, provider: str,
                   reference: str, idempotency_key: str, client_id: int | None = None) -> dict:
    amount = Decimal(str(amount_pkr)).quantize(Decimal("0.01"))
    if amount <= 0: raise ValueError("Payment amount must be greater than zero.")
    if not idempotency_key.strip(): raise ValueError("Idempotency-Key is required.")
    with get_engine().begin() as conn:
        existing = conn.execute(select(payments).where(
            payments.c.provider == provider, payments.c.idempotency_key == idempotency_key
        )).mappings().first()
        if existing:
            if Decimal(str(existing["amount_pkr"])) != amount or existing["method"] != method:
                raise ValueError("Idempotency key was already used with different payment parameters.")
            return dict(existing)
        reference_row = conn.execute(select(payments).where(
            payments.c.provider == provider, payments.c.reference == reference
        )).mappings().first()
        if reference_row:
            raise ValueError("Payment reference is already in use for this provider.")
        result = conn.execute(insert(payments).values(
            advisor_id=advisor_id, client_id=client_id, amount_pkr=amount, currency="PKR",
            method=method, provider=provider, reference=reference,
            idempotency_key=idempotency_key, status="pending", settlement_status="unsettled",
            refund_status="none", chargeback_status="none", retry_count=0, created_at=_now(), updated_at=_now(),
        ))
        payment_id = result.inserted_primary_key[0]
        return dict(conn.execute(select(payments).where(payments.c.id == payment_id)).mappings().one())


def record_provider_event(*, provider: str, payload: dict, raw_body: bytes, reference: str | None,
                          target_status: str, provider_transaction_id: str | None, amount: Decimal | None = None) -> dict:
    event_id = _event_id(payload, raw_body)
    payload_hash = hashlib.sha256(raw_body).hexdigest()
    with get_engine().begin() as conn:
        existing_event = conn.execute(select(payment_events).where(
            payment_events.c.provider == provider, payment_events.c.event_id == event_id
        )).mappings().first()
        if existing_event:
            return {"duplicate": True, "matched": bool(existing_event.get("payment_id")), "event_id": event_id}
        payment = _find_payment(conn, provider, reference) if reference else None
        if not payment:
            conn.execute(insert(payment_events).values(
                provider=provider, event_id=event_id, event_type=target_status,
                payload_hash=payload_hash, payload=payload, created_at=_now(),
            ))
            return {"duplicate": False, "matched": False, "event_id": event_id}
        if amount is not None and Decimal(str(payment["amount_pkr"])).quantize(Decimal("0.01")) != Decimal(str(amount)).quantize(Decimal("0.01")):
            raise ValueError("Provider amount does not match the recorded payment.")
        current = payment["status"]
        if target_status not in ALLOWED_TRANSITIONS.get(current, set()):
            raise ValueError(f"Invalid payment transition: {current} -> {target_status}")
        values = {"status": target_status, "provider_transaction_id": provider_transaction_id, "updated_at": _now(), "provider_response": payload}
        if target_status == "succeeded":
            values.update({"paid_at": _now()})
        conn.execute(update(payments).where(payments.c.id == payment["id"]).values(**values))
        conn.execute(insert(payment_events).values(
            payment_id=payment["id"], provider=provider, event_id=event_id,
            event_type=target_status, payload_hash=payload_hash, payload=payload, created_at=_now(),
        ))
        return {"duplicate": False, "matched": True, "payment_id": payment["id"], "event_id": event_id, "status": target_status}


def request_refund(payment_id: int, amount: Decimal | None = None) -> dict:
    with get_engine().begin() as conn:
        payment = conn.execute(select(payments).where(payments.c.id == payment_id)).mappings().first()
        if not payment: raise ValueError("Payment not found.")
        if payment["status"] != "succeeded": raise ValueError("Only succeeded payments can be refunded.")
        total = Decimal(str(payment["amount_pkr"])).quantize(Decimal("0.01"))
        already = Decimal(str(payment.get("refunded_amount_pkr") or "0")).quantize(Decimal("0.01"))
        if payment.get("refund_status") == "requested":
            raise ValueError("A refund is already pending provider confirmation.")
        refund_amount = Decimal(str(amount)) if amount is not None else (total - already)
        refund_amount = refund_amount.quantize(Decimal("0.01"))
        if refund_amount <= 0 or already + refund_amount > total: raise ValueError("Refund amount exceeds the remaining refundable amount.")
        conn.execute(update(payments).where(payments.c.id == payment_id).values(refund_status="requested", refund_amount_pkr=refund_amount, updated_at=_now()))
        conn.execute(insert(payment_events).values(payment_id=payment_id, provider=payment["provider"], event_id=f"refund-request-{uuid.uuid4().hex}", event_type="refund_requested", payload_hash=hashlib.sha256(str(refund_amount).encode()).hexdigest(), payload={"amount": str(refund_amount)}, created_at=_now()))
        return dict(payment) | {"refund_amount": str(refund_amount), "refund_status": "requested"}


def mark_refunded(payment_id: int, provider_response: dict | None = None, provider_transaction_id: str | None = None) -> dict:
    with get_engine().begin() as conn:
        payment = conn.execute(select(payments).where(payments.c.id == payment_id)).mappings().first()
        if not payment or payment["status"] != "succeeded": raise ValueError("Only succeeded payments can be completed as refunds.")
        refund_amount = Decimal(str(payment.get("refund_amount_pkr") or "0")).quantize(Decimal("0.01"))
        total = Decimal(str(payment["amount_pkr"])).quantize(Decimal("0.01"))
        already = Decimal(str(payment.get("refunded_amount_pkr") or "0")).quantize(Decimal("0.01"))
        if refund_amount <= 0 or already + refund_amount > total:
            raise ValueError("Invalid refund completion amount.")
        new_total = already + refund_amount
        new_status = "refunded" if new_total == total else "succeeded"
        conn.execute(update(payments).where(payments.c.id == payment_id).values(status=new_status, refund_status="completed", refund_amount_pkr=refund_amount, refunded_amount_pkr=new_total, refund_provider_transaction_id=provider_transaction_id, provider_response=provider_response, updated_at=_now()))
        conn.execute(insert(payment_events).values(payment_id=payment_id, provider=payment["provider"], event_id=f"refund-complete-{uuid.uuid4().hex}", event_type="refund_completed", payload_hash=hashlib.sha256(json.dumps(provider_response or {}, sort_keys=True).encode()).hexdigest(), payload={"amount": str(refund_amount), "total_refunded": str(new_total)}, created_at=_now()))
        return {"payment_id": payment_id, "status": new_status, "refund_amount": str(refund_amount), "total_refunded": str(new_total)}


def open_chargeback(payment_id: int, payload: dict | None = None) -> dict:
    with get_engine().begin() as conn:
        payment = conn.execute(select(payments).where(payments.c.id == payment_id)).mappings().first()
        if not payment or payment["status"] != "succeeded": raise ValueError("Only succeeded payments can enter chargeback.")
        if Decimal(str(payment.get("refunded_amount_pkr") or "0")) > 0 or payment.get("refund_status") == "requested":
            raise ValueError("Chargeback cannot be opened while a refund is pending or has been completed.")
        conn.execute(update(payments).where(payments.c.id == payment_id).values(status="chargeback", chargeback_status="open", provider_response=payload, updated_at=_now()))
        conn.execute(insert(payment_events).values(payment_id=payment_id, provider=payment["provider"], event_id=f"chargeback-open-{uuid.uuid4().hex}", event_type="chargeback_opened", payload_hash=hashlib.sha256(json.dumps(payload or {}, sort_keys=True).encode()).hexdigest(), payload=payload or {}, created_at=_now()))
        return {"payment_id": payment_id, "status": "chargeback", "chargeback_status": "open"}


def resolve_chargeback(payment_id: int, outcome: str) -> dict:
    if outcome not in {"won", "lost"}:
        raise ValueError("Chargeback outcome must be 'won' or 'lost'.")
    with get_engine().begin() as conn:
        payment = conn.execute(select(payments).where(payments.c.id == payment_id)).mappings().first()
        if not payment or payment["chargeback_status"] != "open":
            raise ValueError("Payment does not have an open chargeback.")
        new_status = "succeeded" if outcome == "won" else "failed"
        conn.execute(update(payments).where(payments.c.id == payment_id).values(
            status=new_status, chargeback_status=outcome, updated_at=_now()
        ))
        conn.execute(insert(payment_events).values(payment_id=payment_id, provider=payment["provider"], event_id=f"chargeback-resolve-{uuid.uuid4().hex}", event_type="chargeback_resolved", payload_hash=hashlib.sha256(outcome.encode()).hexdigest(), payload={"outcome": outcome}, created_at=_now()))
        return {"payment_id": payment_id, "status": new_status, "chargeback_status": outcome}


def reconcile(provider: str, provider_records: list[dict]) -> dict:
    run_reference = f"RECON-{uuid.uuid4().hex[:16].upper()}"
    matched = amount_mismatch = missing_internal = missing_provider = duplicate = 0
    details = []
    seen = set()
    with get_engine().begin() as conn:
        for record in provider_records:
            ref = str(record.get("reference") or record.get("transaction_id") or "")
            amount = Decimal(str(record.get("amount", "0"))).quantize(Decimal("0.01"))
            if ref in seen:
                duplicate += 1; details.append({"reference": ref, "status": "DUPLICATE"}); continue
            seen.add(ref)
            payment = _find_payment(conn, provider, ref)
            if not payment:
                missing_internal += 1; details.append({"reference": ref, "status": "MISSING_INTERNAL"}); continue
            expected = Decimal(str(payment["amount_pkr"])).quantize(Decimal("0.01"))
            if expected != amount:
                amount_mismatch += 1; details.append({"reference": ref, "status": "AMOUNT_MISMATCH", "expected": str(expected), "actual": str(amount)}); continue
            matched += 1
            if payment["status"] == "succeeded" and payment["settlement_status"] != "settled":
                conn.execute(update(payments).where(payments.c.id == payment["id"]).values(settlement_status="settled", settled_at=_now(), updated_at=_now()))
            details.append({"reference": ref, "status": "MATCHED"})
        # Provider-side records are the source for settlement reconciliation.
        pending_rows = conn.execute(select(payments).where(
            payments.c.provider == provider, payments.c.status == "succeeded", payments.c.settlement_status != "settled"
        )).mappings().all()
        provider_refs = {str(x.get("reference") or x.get("transaction_id") or "") for x in provider_records}
        for payment in pending_rows:
            if payment["reference"] not in provider_refs:
                missing_provider += 1
                details.append({"reference": payment["reference"], "status": "MISSING_PROVIDER"})
        result = conn.execute(insert(audit_reconciliation).values(
            provider=provider, run_reference=run_reference, matched=matched, amount_mismatch=amount_mismatch,
            missing_internal=missing_internal, missing_provider=missing_provider, duplicate=duplicate, created_at=_now(), details=details,
        ))
    return {"run_reference": run_reference, "matched": matched, "amount_mismatch": amount_mismatch, "missing_internal": missing_internal, "missing_provider": missing_provider, "duplicate": duplicate, "details": details}


def retry_delay(retry_count: int) -> timedelta:
    return timedelta(seconds=min(1800, 30 * (2 ** max(0, retry_count))))

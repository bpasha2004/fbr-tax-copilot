"""Verified provider webhook ingress with replay, deduplication and state-machine enforcement."""
import hashlib, hmac, json, time
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from config.settings import settings
from src.shared.payment_service import record_provider_event

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])
_WEBHOOK_MAX_AGE = 300

def _get_webhook_secret(provider: str) -> str:
    return getattr(settings, f"{provider.upper()}_WEBHOOK_SECRET", "")

def _verify_hmac(payload: bytes, signature: str, secret: str) -> bool:
    if not secret or not signature: return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.lower())

def _check_timestamp(ts_str: Optional[str]) -> bool:
    if not ts_str: return False
    try:
        ts = int(ts_str); now = int(time.time())
        return 0 <= now - ts <= _WEBHOOK_MAX_AGE
    except (TypeError, ValueError): return False

def _verified_payload(provider: str, body: bytes, signature: str | None, timestamp: str | None) -> dict:
    if not _check_timestamp(timestamp): raise HTTPException(status_code=400, detail="Webhook rejected: missing or expired timestamp")
    if not _verify_hmac(body, signature or "", _get_webhook_secret(provider)): raise HTTPException(status_code=400, detail="Webhook rejected: invalid HMAC signature")
    try: return json.loads(body)
    except json.JSONDecodeError: raise HTTPException(status_code=400, detail="Webhook rejected: malformed JSON payload")

def _process(provider: str, payload: dict, raw: bytes, reference: str | None, amount, success: bool, provider_txn: str | None):
    target = "succeeded" if success else "failed"
    try:
        return record_provider_event(provider=provider, payload=payload, raw_body=raw, reference=reference,
                                     target_status=target, provider_transaction_id=provider_txn,
                                     amount=amount)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

@router.post("/jazzcash")
async def jazzcash_webhook(request: Request, x_webhook_signature: Optional[str] = Header(None), x_webhook_timestamp: Optional[str] = Header(None)):
    body = await request.body(); payload = _verified_payload("jazzcash", body, x_webhook_signature, x_webhook_timestamp)
    ref = payload.get("pp_TxnRefNo") or payload.get("reference")
    status = str(payload.get("pp_ResponseCode") or "")
    result = _process("jazzcash", payload, body, ref, payload.get("pp_Amount") or payload.get("amount"), status == "000", payload.get("pp_TxnRefNo") or payload.get("transactionId"))
    return JSONResponse({"received": True, **result})

@router.post("/easypaisa")
async def easypaisa_webhook(request: Request, x_webhook_signature: Optional[str] = Header(None), x_webhook_timestamp: Optional[str] = Header(None)):
    body = await request.body(); payload = _verified_payload("easypaisa", body, x_webhook_signature, x_webhook_timestamp)
    ref = payload.get("orderRefNum") or payload.get("reference")
    status = str(payload.get("paymentStatus") or "").upper()
    result = _process("easypaisa", payload, body, ref, payload.get("amount"), status == "PAID", payload.get("transactionId") or ref)
    return JSONResponse({"received": True, **result})

@router.post("/raast")
async def raast_webhook(request: Request, x_webhook_signature: Optional[str] = Header(None), x_webhook_timestamp: Optional[str] = Header(None)):
    body = await request.body(); payload = _verified_payload("raast", body, x_webhook_signature, x_webhook_timestamp)
    ref = payload.get("transactionId") or payload.get("reference")
    status = str(payload.get("status") or "").upper()
    result = _process("raast", payload, body, ref, payload.get("amount"), status in {"COMPLETED", "SUCCESS", "SETTLED"}, payload.get("transactionId"))
    return JSONResponse({"received": True, **result})

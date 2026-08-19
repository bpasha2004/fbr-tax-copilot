"""Local payment sandbox: exercises signed webhook flows without pretending to be a real provider."""
import hashlib
import hmac
import json
import os
import time

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="FBR Payment Sandbox")
TARGET_API = os.getenv("TARGET_API", "http://api:8000")
SECRETS = {
    "jazzcash": os.getenv("JAZZCASH_WEBHOOK_SECRET", "sandbox-jazzcash-secret"),
    "easypaisa": os.getenv("EASYPAISA_WEBHOOK_SECRET", "sandbox-easypaisa-secret"),
    "raast": os.getenv("RAAST_WEBHOOK_SECRET", "sandbox-raast-secret"),
}

@app.get("/health")
def health(): return {"status": "ok", "sandbox": True}

@app.post("/simulate/{provider}")
async def simulate(provider: str, reference: str, amount: float, success: bool = True):
    if provider not in SECRETS: return JSONResponse({"error":"unsupported provider"}, status_code=400)
    if provider == "jazzcash": payload = {"reference": reference, "amount": amount, "pp_ResponseCode": "000" if success else "001"}
    elif provider == "easypaisa": payload = {"reference": reference, "amount": amount, "paymentStatus": "PAID" if success else "FAILED"}
    else: payload = {"transactionId": reference, "amount": amount, "status": "COMPLETED" if success else "FAILED"}
    body = json.dumps(payload, separators=(",", ":")).encode()
    ts = str(int(time.time()))
    sig = hmac.new(SECRETS[provider].encode(), body, hashlib.sha256).hexdigest()
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(f"{TARGET_API}/api/v1/webhooks/{provider}", content=body, headers={"X-Webhook-Signature": sig, "X-Webhook-Timestamp": ts, "Content-Type":"application/json"})
    return {"provider":provider,"forwarded":True,"api_status":r.status_code,"api_response":r.json()}

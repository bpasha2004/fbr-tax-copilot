"""Provider adapter boundary.

No undocumented provider endpoint or payload is fabricated here. Live mode
requires the official provider base URL and credentials to be supplied.
"""
from dataclasses import dataclass
import hashlib, hmac, asyncio
import httpx
from config.settings import settings

@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    api_secret: str

class ProviderClient:
    def __init__(self, provider: str):
        key=provider.upper()
        self.config=ProviderConfig(provider, getattr(settings, f"{key}_API_BASE_URL", ""), getattr(settings, f"{key}_API_KEY", ""), getattr(settings, f"{key}_API_SECRET", ""))
        if settings.PAYMENT_MODE == "live" and (not self.config.base_url or not self.config.api_key or not self.config.api_secret):
            raise RuntimeError(f"{provider} live adapter is not configured with official provider endpoint and credentials")
    async def request(self, method: str, path: str, payload: dict | None = None, *, idempotency_key: str | None = None) -> dict:
        """Call an explicitly configured provider endpoint.

        POST/PUT/PATCH retries require an Idempotency-Key because repeating a
        payment mutation without provider-side idempotency can create duplicates.
        GET/HEAD/DELETE may retry without a key.
        """
        if not self.config.base_url:
            raise RuntimeError(f"{self.config.name} endpoint is not configured")
        method = method.upper()
        if method in {"POST", "PUT", "PATCH"} and not idempotency_key:
            raise ValueError("Provider mutation requests require an Idempotency-Key")
        body = payload or {}
        raw = __import__('json').dumps(body, sort_keys=True, separators=(',', ':')).encode()
        signature = hmac.new(self.config.api_secret.encode(), raw, hashlib.sha256).hexdigest()
        headers = {"Authorization": f"Bearer {self.config.api_key}", "X-Request-Signature": signature, "Content-Type": "application/json"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        max_attempts = max(1, settings.PAYMENT_MAX_RETRIES if method in {"GET", "HEAD", "DELETE"} or idempotency_key else 1)
        transient = {408, 425, 429, 500, 502, 503, 504}
        last_error = None
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient(timeout=settings.PAYMENT_HTTP_TIMEOUT_SECONDS) as client:
                    response = await client.request(method, self.config.base_url.rstrip('/') + '/' + path.lstrip('/'), json=body, headers=headers)
                if response.status_code in transient and attempt + 1 < max_attempts:
                    await asyncio.sleep(min(30, 0.5 * (2 ** attempt)))
                    continue
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt + 1 >= max_attempts: raise
                await asyncio.sleep(min(30, 0.5 * (2 ** attempt)))
        raise RuntimeError(f"Provider request failed: {last_error}")

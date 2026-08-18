"""
Bootstrapped Authentication — Zero External Cost
Strategy 1: Google OIDC (Google Sign-In) — free, no API cost
Strategy 2: TOTP (Time-based OTP via pyotp) — app-based, no SMS cost

Flow:
  1. User initiates login → redirected to Google OAuth2 consent
  2. Google returns authorization code → exchange for id_token
  3. Verify id_token against Google public keys (free JWKS endpoint)
  4. Create local session (SQLite), issue signed JWT via python-jose

No paid services. No Twilio. No Auth0. No Firebase.
"""
import hashlib
import hmac
import json
import os
import secrets
import time
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

from config.settings import settings
from sqlalchemy import select
from src.shared.models import get_engine, advisors, sessions, oauth_states
from sqlalchemy import and_

# ── Google OIDC constants ─────────────────────────────────────────────────────
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
GOOGLE_TOKEN_URL     = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL  = "https://openid.googleapis.com/v2/userinfo"

# Read from environment — set in config/.env.dev
GOOGLE_CLIENT_ID     = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI  = settings.GOOGLE_REDIRECT_URI


# ── Simple HMAC-SHA256 session token (no JWT library required) ────────────────

def _sign_token(payload: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _verify_token(token: str, secret: str) -> Optional[dict]:
    parts = token.rsplit(".", 1)
    if len(parts) != 2:
        return None
    payload_str, sig = parts
    expected = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        return json.loads(payload_str)
    except Exception:
        return None



def _as_utc(value) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def revoke_session(token: str) -> bool:
    token_hash = _hash_token(token)
    with get_engine().begin() as conn:
        result = conn.execute(sessions.update().where(sessions.c.token_hash == token_hash).values(revoked=True))
        return result.rowcount > 0


def create_session_token(advisor_id: int, email: str, ttl_hours: int | None = None, role: str = "advisor", mfa_verified: bool = False) -> str:
    ttl_hours = ttl_hours or settings.SESSION_TTL_HOURS
    payload = json.dumps({
        "advisor_id": advisor_id, "email": email, "role": role,
        "mfa_verified": bool(mfa_verified),
        "exp": int(time.time()) + ttl_hours * 3600,
        "jti": secrets.token_hex(16),
    }, separators=(",", ":"))
    token = _sign_token(payload, settings.SECRET_KEY)
    with get_engine().begin() as conn:
        conn.execute(sessions.delete().where(and_(sessions.c.advisor_id == advisor_id, sessions.c.expires_at < datetime.now(timezone.utc))))
        conn.execute(sessions.insert().values(
            advisor_id=advisor_id, token_hash=_hash_token(token),
            expires_at=datetime.fromtimestamp(json.loads(payload)["exp"], tz=timezone.utc),
            revoked=False,
        ))
    return token


def decode_session_token(token: str) -> Optional[dict]:
    data = _verify_token(token, settings.SECRET_KEY)
    if not data:
        return None
    if data.get("exp", 0) < int(time.time()):
        return None
    return data


# ── Google OIDC helpers ───────────────────────────────────────────────────────

def create_oauth_state(ttl_seconds: int = 600) -> str:
    payload = json.dumps({
        "purpose": "google_oauth", "exp": int(time.time()) + ttl_seconds,
        "nonce": secrets.token_hex(16),
    }, separators=(",", ":"))
    state = _sign_token(payload, settings.SECRET_KEY)
    with get_engine().begin() as conn:
        conn.execute(oauth_states.insert().values(
            state_hash=_hash_token(state),
            expires_at=datetime.fromtimestamp(json.loads(payload)["exp"], tz=timezone.utc),
            used=False,
        ))
    return state

def verify_oauth_state(state: str) -> bool:
    data = _verify_token(state, settings.SECRET_KEY)
    if not data or data.get("purpose") != "google_oauth" or data.get("exp", 0) < int(time.time()):
        return False
    with get_engine().begin() as conn:
        row = conn.execute(oauth_states.select().where(oauth_states.c.state_hash == _hash_token(state))).mappings().first()
        if not row or row["used"] or _as_utc(row["expires_at"]) < datetime.now(timezone.utc):
            return False
        conn.execute(oauth_states.update().where(oauth_states.c.id == row["id"]).values(used=True))
    return True

def build_google_auth_url(state: str) -> str:
    """
    Returns the Google OAuth2 authorization URL.
    Redirect this URL to the user's browser.
    """
    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         state,
        "access_type":   "offline",
        "prompt":        "select_account",
    }
    query = urlencode(params)
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


async def exchange_google_code(code: str) -> dict:
    """
    Exchange authorization code for Google user info.
    Returns: {"email": str, "name": str, "sub": str}
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code":          code,
                "client_id":     GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri":  GOOGLE_REDIRECT_URI,
                "grant_type":    "authorization_code",
            },
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        user_resp.raise_for_status()
        return user_resp.json()


# ── TOTP 2FA (app-based, zero cost) ──────────────────────────────────────────

def generate_totp_secret() -> str:
    """Generate a base32 TOTP secret for Google Authenticator."""
    try:
        import pyotp
        return pyotp.random_base32()
    except ImportError:
        import base64
        return base64.b32encode(os.urandom(20)).decode()


def get_totp_qr_url(email: str, secret: str) -> str:
    """Returns otpauth:// URL for QR code scanning in Google Authenticator."""
    try:
        import pyotp
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name="FBR Tax Copilot")
    except ImportError:
        return f"otpauth://totp/FBR%20Tax%20Copilot:{email}?secret={secret}&issuer=FBR%20Tax%20Copilot"


def verify_totp(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code against the stored secret."""
    try:
        import pyotp
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
    except ImportError:
        return False


# ── FastAPI dependency ────────────────────────────────────────────────────────

def get_current_advisor(token: str) -> Optional[dict]:
    """
    Decode the signed session token and verify the advisor still exists and is active.
    Returns None if the token is invalid, expired, or the account is inactive.
    """
    payload = decode_session_token(token)
    if not payload:
        return None

    advisor_id = payload.get("advisor_id")
    if not isinstance(advisor_id, int):
        return None

    try:
        with get_engine().connect() as conn:
            token_hash = _hash_token(token)
            session_row = conn.execute(select(sessions).where(sessions.c.token_hash == token_hash)).mappings().first()
            if not session_row or session_row["revoked"] or _as_utc(session_row["expires_at"]) < datetime.now(timezone.utc):
                return None
            row = conn.execute(select(advisors).where(advisors.c.id == advisor_id)).mappings().first()
    except Exception:
        return None

    if not row or not row.get("active", False):
        return None

    return {
        **payload,
        "display_name": row.get("display_name"),
        "plan": row.get("plan", "free"),
        "role": row.get("role", "advisor"),
        "mfa_enabled": bool(row.get("mfa_enabled", False)),
    }


def require_role(advisor: dict, *allowed: str) -> dict:
    role = advisor.get("role", "advisor")
    if role not in allowed:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Insufficient role permissions.")
    return advisor


def require_write_access(advisor: dict) -> dict:
    """Require an active session and MFA for writes when production policy requires it."""
    from fastapi import HTTPException
    if settings.REQUIRE_MFA_FOR_WRITES and settings.ENV == "production" and advisor.get("role") not in {"admin", "advisor", "reviewer"}:
        raise HTTPException(status_code=403, detail="This role cannot perform write operations.")
    if settings.REQUIRE_MFA_FOR_WRITES and settings.ENV == "production" and not advisor.get("mfa_verified"):
        raise HTTPException(status_code=401, detail="MFA verification required for write operations.")
    return advisor

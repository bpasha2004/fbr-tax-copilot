"""
Authentication Routes — Gmail OIDC + TOTP
Zero external cost. Google Sign-In is free for all users.
TOTP uses Google Authenticator (no SMS, no cost).
"""
import secrets
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from typing import Optional

from src.shared.auth import (
    build_google_auth_url,
    exchange_google_code,
    create_session_token,
    get_current_advisor,
    generate_totp_secret,
    get_totp_qr_url,
    verify_totp,
    create_oauth_state,
    verify_oauth_state,
    revoke_session,
    GOOGLE_CLIENT_ID,
)
from src.shared.models import init_db, get_engine, advisors
from sqlalchemy import select, insert, update
from datetime import datetime, timezone
from config.settings import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _get_or_create_advisor(google_user: dict) -> dict:
    """Find or create an advisor from Google OIDC user info."""
    engine = get_engine()
    email  = google_user.get("email", "")
    sub    = google_user.get("sub", "")
    name   = google_user.get("name", email.split("@")[0])

    with engine.begin() as conn:
        row = conn.execute(
            select(advisors).where(advisors.c.email == email)
        ).mappings().first()

        if row:
            conn.execute(
                update(advisors)
                .where(advisors.c.email == email)
                .values(last_login=datetime.now(timezone.utc), google_sub=sub)
            )
            updated = conn.execute(
                select(advisors).where(advisors.c.id == row["id"])
            ).mappings().first()
            return dict(updated or row)

        role = "admin" if email.lower().strip() in {e.strip().lower() for e in settings.BOOTSTRAP_ADMIN_EMAILS.split(",") if e.strip()} else "advisor"
        result = conn.execute(
            insert(advisors).values(
                email=email,
                google_sub=sub,
                display_name=name,
                active=True,
                plan="free",
                role=role,
                created_at=datetime.now(timezone.utc),
                last_login=datetime.now(timezone.utc),
            )
        )
        new_id = result.inserted_primary_key[0]
        return {"id": new_id, "email": email, "display_name": name, "role": role, "plan": "free"}


# ── Development login ─────────────────────────────────────────────────────────

class DevLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, examples=["advisor@example.com"])
    display_name: str = Field("Development Advisor", min_length=1, max_length=128)

@router.post("/dev-login")
def dev_login(body: DevLoginRequest):
    """Create a local advisor session for development/demo use only."""
    from config.settings import settings
    if settings.ENV != "development":
        raise HTTPException(status_code=404, detail="Not found")

    init_db()
    advisor = _get_or_create_advisor({
        "email": body.email,
        "name": body.display_name,
        "sub": f"dev:{body.email}",
    })
    token = create_session_token(advisor_id=advisor["id"], email=advisor["email"], role=advisor.get("role", "advisor"))
    return {
        "token": token,
        "advisor_id": advisor["id"],
        "email": advisor["email"],
        "display_name": advisor.get("display_name", body.display_name),
        "plan": advisor.get("plan", "free"),
        "role": advisor.get("role", "advisor"),
        "mfa_verified": bool(advisor.get("mfa_verified", True)),
    }

# ── OAuth2 flow ───────────────────────────────────────────────────────────────

@router.get("/login")
def google_login():
    """
    Step 1: Redirect user to Google Sign-In.
    Frontend should navigate to this URL or open it in a popup.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID in config/.env.dev"
        )
    state = create_oauth_state()
    url   = build_google_auth_url(state=state)
    return {"auth_url": url, "state": state}


@router.get("/callback")
async def google_callback(code: str, state: str):
    """
    Step 2: Google redirects here with authorization code.
    Exchange code for user info, create session, return token.
    """
    if not verify_oauth_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")

    try:
        google_user = await exchange_google_code(code)
    except Exception:
        raise HTTPException(status_code=400, detail="Google authentication failed.")

    init_db()
    advisor = _get_or_create_advisor(google_user)
    token   = create_session_token(
        advisor_id=advisor.get("id", advisor.get("advisor_id")),
        email=advisor["email"],
        role=advisor.get("role", "advisor"),
        mfa_verified=not bool(advisor.get("mfa_enabled", False)),
    )

    return {
        "token":        token,
        "advisor_id":   advisor.get("id", advisor.get("advisor_id")),
        "email":        advisor["email"],
        "display_name": advisor.get("display_name", ""),
        "plan":         advisor.get("plan", "free"),
        "message":      "Login successful. Include token in Authorization: Bearer <token> header.",
    }


# ── Session validation ────────────────────────────────────────────────────────

@router.post("/logout")
def logout(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    revoke_session(authorization[7:].strip())
    return {"status": "logged_out"}


@router.get("/me")
def get_current_user(authorization: str = Header(None)):
    """Returns current advisor info from session token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    token   = authorization.removeprefix("Bearer ").strip()
    advisor = get_current_advisor(token)
    if not advisor:
        raise HTTPException(status_code=401, detail="Session expired or invalid.")
    return advisor


# ── TOTP 2FA setup ────────────────────────────────────────────────────────────

@router.post("/totp/setup")
def setup_totp(authorization: str = Header(None)):
    """
    Generate a TOTP secret for the advisor.
    Returns QR code URL for scanning in Google Authenticator (free, no SMS).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    token   = authorization.removeprefix("Bearer ").strip()
    advisor = get_current_advisor(token)
    if not advisor:
        raise HTTPException(status_code=401, detail="Session expired.")

    secret  = generate_totp_secret()
    qr_url  = get_totp_qr_url(advisor["email"], secret)

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            update(advisors)
            .where(advisors.c.email == advisor["email"])
            .values(totp_secret=secret)
        )

    return {
        "totp_secret": secret,
        "qr_url":      qr_url,
        "instructions": (
            "Scan the QR URL with Google Authenticator. "
            "Then verify with POST /api/v1/auth/totp/verify before 2FA is active."
        ),
    }


class TOTPVerifyRequest(BaseModel):
    code: str = Field(..., examples=["123456"])


@router.post("/totp/verify")
def verify_totp_code(body: TOTPVerifyRequest, authorization: str = Header(None)):
    """Verify a 6-digit TOTP code to confirm 2FA setup."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    token   = authorization.removeprefix("Bearer ").strip()
    advisor = get_current_advisor(token)
    if not advisor:
        raise HTTPException(status_code=401, detail="Session expired.")

    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(advisors.c.totp_secret).where(advisors.c.email == advisor["email"])
        ).first()

    if not row or not row[0]:
        raise HTTPException(status_code=400, detail="TOTP not set up. Call /totp/setup first.")

    if not verify_totp(row[0], body.code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code.")

    with engine.begin() as conn:
        conn.execute(update(advisors).where(advisors.c.id == advisor["advisor_id"]).values(mfa_enabled=True))
    refreshed = create_session_token(
        advisor_id=advisor["advisor_id"],
        email=advisor["email"],
        role=advisor.get("role", "advisor"),
        mfa_verified=True,
    )
    return {"status": "enabled", "mfa_verified": True, "token": refreshed}


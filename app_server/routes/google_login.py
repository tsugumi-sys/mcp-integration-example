from __future__ import annotations

import time
import uuid
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from auth.session import create_session

router = APIRouter()

COOKIE_NAME = "admin_session"
POST_LOGIN_REDIRECT_COOKIE = "post_login_redirect"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
STATE_PROVIDER = "google_admin"


def _create_state(conn) -> str:
    state = str(uuid.uuid4())
    expires_at = int(time.time()) + 600
    conn.execute(
        "INSERT INTO oauth_states (state, credential_id, provider, expires_at) VALUES (?, ?, ?, ?)",
        (state, None, STATE_PROVIDER, expires_at),
    )
    conn.commit()
    return state


def _consume_state(conn, state: str) -> bool:
    row = conn.execute(
        "SELECT expires_at FROM oauth_states WHERE state = ? AND provider = ?",
        (state, STATE_PROVIDER),
    ).fetchone()
    if not row:
        return False
    conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
    conn.commit()
    return row["expires_at"] >= int(time.time())


def _is_allowed_email(settings, email: str, hosted_domain: str | None) -> bool:
    if settings.google_login_allowed_emails:
        return email in settings.google_login_allowed_emails
    if settings.google_login_allowed_domain:
        return hosted_domain == settings.google_login_allowed_domain or email.endswith(
            f"@{settings.google_login_allowed_domain}"
        )
    return True


async def _exchange_code_for_tokens(
    code: str, redirect_uri: str, client_id: str, client_secret: str
) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail="google token exchange failed")
    return response.json()


async def _verify_id_token(id_token: str, expected_audience: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail="google id token verification failed")
    payload = response.json()
    if payload.get("aud") != expected_audience:
        raise HTTPException(status_code=400, detail="google id token audience mismatch")
    if payload.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=400, detail="google id token issuer mismatch")
    if payload.get("email_verified") not in {"true", True}:
        raise HTTPException(status_code=403, detail="google email is not verified")
    return payload


@router.get("/auth/login")
async def login(request: Request):
    settings = request.app.state.settings
    if not settings.google_login_client_id or not settings.google_login_client_secret:
        raise HTTPException(
            status_code=500,
            detail="google admin login is not configured",
        )
    state = _create_state(request.app.state.db)
    redirect_uri = str(request.url_for("google_login_callback"))
    params = {
        "client_id": settings.google_login_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/auth/google/callback", name="google_login_callback")
async def google_callback(request: Request, code: str, state: str):
    conn = request.app.state.db
    settings = request.app.state.settings
    if not _consume_state(conn, state):
        raise HTTPException(status_code=400, detail="invalid state")

    redirect_uri = str(request.url_for("google_login_callback"))
    token_payload = await _exchange_code_for_tokens(
        code,
        redirect_uri,
        settings.google_login_client_id,
        settings.google_login_client_secret,
    )
    id_token = token_payload.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="google id token missing")
    identity = await _verify_id_token(id_token, settings.google_login_client_id)
    email = identity.get("email")
    hosted_domain = identity.get("hd")
    if not email:
        raise HTTPException(status_code=400, detail="google email missing")
    if not _is_allowed_email(settings, email, hosted_domain):
        raise HTTPException(status_code=403, detail="google account is not allowed")

    session_id = create_session(
        conn, email, settings.admin_session_ttl_seconds
    )
    redirect_target = request.cookies.get(POST_LOGIN_REDIRECT_COOKIE) or "/credentials"
    response = RedirectResponse(redirect_target, status_code=302)
    response.set_cookie(COOKIE_NAME, session_id, httponly=True)
    response.delete_cookie(POST_LOGIN_REDIRECT_COOKIE)
    return response

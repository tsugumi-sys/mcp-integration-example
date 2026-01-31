from __future__ import annotations

import json
import time
import uuid
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _create_state(conn, credential_id: str, provider: str) -> str:
    state = str(uuid.uuid4())
    expires_at = int(time.time()) + 600
    conn.execute(
        "INSERT INTO oauth_states (state, credential_id, provider, expires_at) VALUES (?, ?, ?, ?)",
        (state, credential_id, provider, expires_at),
    )
    conn.commit()
    return state


def _consume_state(conn, state: str, provider: str) -> str | None:
    row = conn.execute(
        "SELECT credential_id, expires_at FROM oauth_states WHERE state = ? AND provider = ?",
        (state, provider),
    ).fetchone()
    if not row:
        return None
    conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
    conn.commit()
    if row["expires_at"] < int(time.time()):
        return None
    return row["credential_id"]


@router.post("/credentials/{credential_id}/oauth/start")
async def oauth_start(request: Request, credential_id: str):
    conn = request.app.state.db
    settings = request.app.state.settings
    credential = conn.execute(
        "SELECT provider FROM credentials WHERE id = ?",
        (credential_id,),
    ).fetchone()
    if not credential:
        raise HTTPException(status_code=404, detail="credential not found")
    provider = credential["provider"]
    if provider != "google_calendar":
        raise HTTPException(status_code=400, detail="unsupported provider")
    if not settings.google_client_id:
        raise HTTPException(status_code=400, detail="GOOGLE_CLIENT_ID not set")

    state = _create_state(conn, credential_id, provider)
    redirect_uri = request.url_for("oauth_callback", provider=provider)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/calendar",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/oauth/{provider}/callback", name="oauth_callback")
async def oauth_callback(request: Request, provider: str, code: str, state: str):
    conn = request.app.state.db
    settings = request.app.state.settings
    credential_id = _consume_state(conn, state, provider)
    if not credential_id:
        raise HTTPException(status_code=400, detail="invalid state")
    if provider != "google_calendar":
        raise HTTPException(status_code=400, detail="unsupported provider")
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=400, detail="google oauth not configured")

    redirect_uri = request.url_for("oauth_callback", provider=provider)
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=data)
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail="token exchange failed")
    payload = response.json()
    now = int(time.time())
    conn.execute(
        "REPLACE INTO oauth_tokens (credential_id, access_token, refresh_token, expiry, scope, token_type, extra_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            credential_id,
            payload.get("access_token"),
            payload.get("refresh_token"),
            now + int(payload.get("expires_in", 0)),
            payload.get("scope"),
            payload.get("token_type"),
            json.dumps(payload),
            now,
        ),
    )
    conn.execute(
        "UPDATE credentials SET status = ?, updated_at = ? WHERE id = ?",
        ("connected", now, credential_id),
    )
    conn.commit()
    return RedirectResponse(f"/credentials/{credential_id}")

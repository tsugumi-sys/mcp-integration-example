from __future__ import annotations

import time
import uuid
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from auth.dummy_oauth import consume_code, create_code
from auth.session import create_session

router = APIRouter()

TEMPLATES = Jinja2Templates(directory="templates")
COOKIE_NAME = "admin_session"


def _create_state(conn) -> str:
    state = str(uuid.uuid4())
    now = int(time.time())
    expires_at = now + 600
    conn.execute(
        "INSERT INTO oauth_states (state, credential_id, provider, expires_at) VALUES (?, ?, ?, ?)",
        (state, None, "dummy_admin", expires_at),
    )
    conn.commit()
    return state


def _validate_state(conn, state: str) -> bool:
    row = conn.execute(
        "SELECT state, expires_at FROM oauth_states WHERE state = ? AND provider = ?",
        (state, "dummy_admin"),
    ).fetchone()
    if not row:
        return False
    conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
    conn.commit()
    return row["expires_at"] >= int(time.time())


@router.get("/auth/login")
async def login(request: Request):
    conn = request.app.state.db
    state = _create_state(conn)
    redirect_uri = request.url_for("dummy_callback")
    url = f"/oauth/dummy/authorize?state={state}&redirect_uri={redirect_uri}"
    return RedirectResponse(url)


@router.get("/oauth/dummy/authorize", response_class=HTMLResponse)
async def dummy_authorize(request: Request, state: str, redirect_uri: str):
    return TEMPLATES.TemplateResponse(
        "dummy_login.html",
        {"request": request, "state": state, "redirect_uri": redirect_uri},
    )


@router.post("/oauth/dummy/authorize")
async def dummy_authorize_post(
    request: Request,
    email: str = Form(""),
    state: str = Form(""),
    redirect_uri: str = Form(""),
):
    if not email:
        raise HTTPException(status_code=400, detail="email required")
    conn = request.app.state.db
    code = create_code(conn, email=email, state=state, ttl_seconds=300)
    return RedirectResponse(f"{redirect_uri}?code={code}&state={state}", status_code=302)


@router.post("/oauth/dummy/token")
async def dummy_token(
    request: Request,
    code: str = Form(""),
    client_id: str = Form(""),
    client_secret: str = Form(""),
):
    settings = request.app.state.settings
    if client_id != settings.dummy_oauth_client_id or client_secret != settings.dummy_oauth_client_secret:
        raise HTTPException(status_code=401, detail="invalid client credentials")
    conn = request.app.state.db
    data = consume_code(conn, code)
    if not data:
        raise HTTPException(status_code=400, detail="invalid code")
    return {"access_token": str(uuid.uuid4()), "token_type": "Bearer", "email": data["email"]}


@router.get("/oauth/dummy/callback", name="dummy_callback")
async def dummy_callback(request: Request, code: str, state: str):
    conn = request.app.state.db
    if not _validate_state(conn, state):
        raise HTTPException(status_code=400, detail="invalid state")
    data = consume_code(conn, code)
    if not data:
        raise HTTPException(status_code=400, detail="invalid code")
    session_id = create_session(conn, data["email"], request.app.state.settings.admin_session_ttl_seconds)
    response = RedirectResponse("/credentials", status_code=302)
    response.set_cookie(COOKIE_NAME, session_id, httponly=True)
    return response

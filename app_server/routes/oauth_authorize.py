from __future__ import annotations

import secrets
import time
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from auth.session import get_session

router = APIRouter()

ADMIN_SESSION_COOKIE = "admin_session"
POST_LOGIN_REDIRECT_COOKIE = "post_login_redirect"


def _require_registered_client(conn, client_id: str):
    client = conn.execute(
        """
        SELECT client_id, redirect_uris_json, response_types_json, grant_types_json, scope
        FROM oauth_clients
        WHERE client_id = ?
        """,
        (client_id,),
    ).fetchone()
    if not client:
        raise HTTPException(status_code=400, detail="unknown client_id")
    return client


@router.get("/oauth/authorize")
async def oauth_authorize(
    request: Request,
    client_id: str,
    redirect_uri: str,
    response_type: str = "code",
    scope: str | None = None,
    state: str | None = None,
):
    if response_type != "code":
        raise HTTPException(status_code=400, detail="unsupported response_type")

    conn = request.app.state.db
    client = _require_registered_client(conn, client_id)

    import json

    redirect_uris = json.loads(client["redirect_uris_json"] or "[]")
    if redirect_uri not in redirect_uris:
        raise HTTPException(status_code=400, detail="redirect_uri mismatch")
    response_types = json.loads(client["response_types_json"] or "[]")
    if "code" not in response_types:
        raise HTTPException(status_code=400, detail="client does not allow authorization code flow")
    grant_types = json.loads(client["grant_types_json"] or "[]")
    if "authorization_code" not in grant_types:
        raise HTTPException(status_code=400, detail="client does not allow authorization_code grant")

    session_id = request.cookies.get(ADMIN_SESSION_COOKIE)
    session = get_session(conn, session_id) if session_id else None
    if not session:
        response = RedirectResponse("/auth/login", status_code=302)
        response.set_cookie(
            POST_LOGIN_REDIRECT_COOKIE,
            str(request.url),
            httponly=True,
        )
        return response

    now = int(time.time())
    code = secrets.token_urlsafe(32)
    requested_scope = (scope or client["scope"] or "mcp").strip() or "mcp"
    conn.execute(
        """
        INSERT INTO oauth_authorization_codes (
            code,
            client_id,
            redirect_uri,
            subject,
            scope,
            expires_at,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            code,
            client_id,
            redirect_uri,
            session["email"],
            requested_scope,
            now + 300,
            now,
        ),
    )
    conn.commit()

    query = {"code": code}
    if state:
        query["state"] = state
    return RedirectResponse(f"{redirect_uri}?{urlencode(query)}", status_code=302)

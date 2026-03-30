from __future__ import annotations

import base64
import json
import secrets
import time

from fastapi import APIRouter, HTTPException, Request

from auth.jwt import issue_jwt
from shared.models import AuthTokenResponse

router = APIRouter()


def _decode_basic_auth(header: str | None) -> tuple[str, str] | None:
    if not header or not header.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(header[6:]).decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid basic auth header") from exc
    if ":" not in decoded:
        raise HTTPException(status_code=401, detail="invalid basic auth header")
    client_id, client_secret = decoded.split(":", 1)
    return client_id, client_secret


async def _read_token_request(request: Request) -> dict[str, str]:
    content_type = (request.headers.get("content-type") or "").split(";")[0].strip()
    if content_type == "application/json":
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="invalid json payload")
        return {str(key): str(value) for key, value in payload.items() if value is not None}
    form = await request.form()
    return {str(key): str(value) for key, value in form.items() if value is not None}


def _load_registered_client(conn, client_id: str):
    return conn.execute(
        """
        SELECT client_id, client_secret, grant_types_json, scope, token_endpoint_auth_method
        FROM oauth_clients
        WHERE client_id = ?
        """,
        (client_id,),
    ).fetchone()


def _consume_authorization_code(conn, code: str):
    row = conn.execute(
        """
        SELECT code, client_id, redirect_uri, subject, scope, expires_at
        FROM oauth_authorization_codes
        WHERE code = ?
        """,
        (code,),
    ).fetchone()
    if not row:
        return None
    conn.execute("DELETE FROM oauth_authorization_codes WHERE code = ?", (code,))
    conn.commit()
    return row


def _consume_refresh_token(conn, refresh_token: str):
    row = conn.execute(
        """
        SELECT refresh_token, client_id, subject, scope, expires_at
        FROM oauth_refresh_tokens
        WHERE refresh_token = ?
        """,
        (refresh_token,),
    ).fetchone()
    if not row:
        return None
    conn.execute(
        "DELETE FROM oauth_refresh_tokens WHERE refresh_token = ?",
        (refresh_token,),
    )
    conn.commit()
    return row


def _issue_refresh_token(conn, settings, client_id: str, subject: str, scope: str) -> str:
    now = int(time.time())
    refresh_token = secrets.token_urlsafe(48)
    conn.execute(
        """
        INSERT INTO oauth_refresh_tokens (
            refresh_token,
            client_id,
            subject,
            scope,
            expires_at,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            refresh_token,
            client_id,
            subject,
            scope,
            now + settings.oauth_refresh_ttl_seconds,
            now,
        ),
    )
    conn.commit()
    return refresh_token


@router.post("/auth/token", response_model=AuthTokenResponse)
async def issue_token(request: Request) -> AuthTokenResponse:
    payload = await _read_token_request(request)
    grant_type = payload.get("grant_type") or "client_credentials"
    if grant_type not in {"client_credentials", "authorization_code", "refresh_token"}:
        raise HTTPException(status_code=400, detail="unsupported grant_type")

    basic_auth = _decode_basic_auth(request.headers.get("authorization"))
    client_id = payload.get("client_id")
    client_secret = payload.get("client_secret")
    if basic_auth:
        client_id, client_secret = basic_auth
    if not client_id or not client_secret:
        raise HTTPException(status_code=401, detail="missing client credentials")

    conn = request.app.state.db
    client = _load_registered_client(conn, client_id)
    if not client:
        raise HTTPException(status_code=401, detail="invalid client credentials")
    if client["client_secret"] != client_secret:
        raise HTTPException(status_code=401, detail="invalid client credentials")
    if client["token_endpoint_auth_method"] == "client_secret_basic" and not basic_auth:
        raise HTTPException(status_code=401, detail="client_secret_basic required")
    if client["token_endpoint_auth_method"] == "client_secret_post" and basic_auth:
        raise HTTPException(status_code=401, detail="client_secret_post required")

    grant_types = json.loads(client["grant_types_json"])
    if grant_type not in grant_types:
        raise HTTPException(status_code=400, detail="grant_type not allowed for client")

    settings = request.app.state.settings
    subject = client_id
    refresh_token = None
    token_scope = (client["scope"] or "mcp").strip() or "mcp"
    if grant_type == "authorization_code":
        code = payload.get("code")
        redirect_uri = payload.get("redirect_uri")
        if not code or not redirect_uri:
            raise HTTPException(status_code=400, detail="code and redirect_uri are required")
        code_row = _consume_authorization_code(conn, code)
        if not code_row:
            raise HTTPException(status_code=400, detail="invalid authorization code")
        if code_row["expires_at"] <= int(time.time()):
            raise HTTPException(status_code=400, detail="authorization code expired")
        if code_row["client_id"] != client_id:
            raise HTTPException(status_code=400, detail="authorization code client mismatch")
        if code_row["redirect_uri"] != redirect_uri:
            raise HTTPException(status_code=400, detail="redirect_uri mismatch")
        subject = code_row["subject"]
        token_scope = (code_row["scope"] or token_scope).strip() or "mcp"
        if "refresh_token" in grant_types:
            refresh_token = _issue_refresh_token(
                conn, settings, client_id, subject, token_scope
            )
    elif grant_type == "refresh_token":
        incoming_refresh_token = payload.get("refresh_token")
        if not incoming_refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token is required")
        refresh_row = _consume_refresh_token(conn, incoming_refresh_token)
        if not refresh_row:
            raise HTTPException(status_code=400, detail="invalid refresh_token")
        if refresh_row["expires_at"] <= int(time.time()):
            raise HTTPException(status_code=400, detail="refresh_token expired")
        if refresh_row["client_id"] != client_id:
            raise HTTPException(status_code=400, detail="refresh_token client mismatch")
        subject = refresh_row["subject"]
        token_scope = (refresh_row["scope"] or token_scope).strip() or "mcp"
        refresh_token = _issue_refresh_token(
            conn, settings, client_id, subject, token_scope
        )

    token, _exp = issue_jwt(
        settings.jwt_secret,
        settings.jwt_issuer,
        settings.jwt_ttl_seconds,
        subject,
    )
    return AuthTokenResponse(
        access_token=token,
        expires_in=settings.jwt_ttl_seconds,
        refresh_token=refresh_token,
    )

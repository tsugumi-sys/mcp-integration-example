from __future__ import annotations

import json
import secrets
import time
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

SUPPORTED_GRANT_TYPES = {"client_credentials", "authorization_code", "refresh_token"}
SUPPORTED_AUTH_METHODS = {"client_secret_post", "client_secret_basic"}


def _is_valid_redirect_uri(uri: str) -> bool:
    parsed = urlparse(uri)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


@router.post("/oauth/register")
async def oauth_register(request: Request) -> dict:
    payload = await request.json()
    client_name = (payload.get("client_name") or "").strip()
    if not client_name:
        raise HTTPException(status_code=400, detail="client_name is required")

    grant_types = payload.get("grant_types") or ["client_credentials"]
    if not isinstance(grant_types, list) or not grant_types:
        raise HTTPException(status_code=400, detail="grant_types must be a non-empty list")
    unsupported_grants = [grant for grant in grant_types if grant not in SUPPORTED_GRANT_TYPES]
    if unsupported_grants:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported grant_types: {', '.join(unsupported_grants)}",
        )
    if "refresh_token" in grant_types and "authorization_code" not in grant_types:
        raise HTTPException(
            status_code=400,
            detail="refresh_token grant requires authorization_code",
        )

    token_endpoint_auth_method = payload.get("token_endpoint_auth_method") or "client_secret_post"
    if token_endpoint_auth_method not in SUPPORTED_AUTH_METHODS:
        raise HTTPException(status_code=400, detail="unsupported token_endpoint_auth_method")

    redirect_uris = payload.get("redirect_uris") or []
    if not isinstance(redirect_uris, list):
        raise HTTPException(status_code=400, detail="redirect_uris must be a list")
    invalid_redirects = [uri for uri in redirect_uris if not isinstance(uri, str) or not _is_valid_redirect_uri(uri)]
    if invalid_redirects:
        raise HTTPException(status_code=400, detail="invalid redirect_uris")

    response_types = payload.get("response_types")
    if response_types is None:
        response_types = ["code"] if "authorization_code" in grant_types else ["none"]
    if not isinstance(response_types, list) or not response_types:
        raise HTTPException(status_code=400, detail="response_types must be a non-empty list")
    supported_response_types = {"none"}
    if "authorization_code" in grant_types:
        supported_response_types.add("code")
    if any(response_type not in supported_response_types for response_type in response_types):
        raise HTTPException(status_code=400, detail="unsupported response_types")

    if "authorization_code" in grant_types and not redirect_uris:
        raise HTTPException(status_code=400, detail="redirect_uris required for authorization_code")

    scope = (payload.get("scope") or "mcp").strip() or "mcp"
    now = int(time.time())
    client_id = secrets.token_urlsafe(24)
    client_secret = secrets.token_urlsafe(36)

    request.app.state.db.execute(
        """
        INSERT INTO oauth_clients (
            client_id,
            client_secret,
            client_name,
            redirect_uris_json,
            grant_types_json,
            response_types_json,
            scope,
            token_endpoint_auth_method,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            client_id,
            client_secret,
            client_name,
            json.dumps(redirect_uris),
            json.dumps(grant_types),
            json.dumps(response_types),
            scope,
            token_endpoint_auth_method,
            now,
            now,
        ),
    )
    request.app.state.db.commit()

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_id_issued_at": now,
        "client_secret_expires_at": 0,
        "client_name": client_name,
        "redirect_uris": redirect_uris,
        "grant_types": grant_types,
        "response_types": response_types,
        "scope": scope,
        "token_endpoint_auth_method": token_endpoint_auth_method,
    }

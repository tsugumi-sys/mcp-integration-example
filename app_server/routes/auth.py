from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from auth.jwt import issue_jwt
from shared.models import AuthTokenRequest, AuthTokenResponse

router = APIRouter()


@router.post("/auth/token", response_model=AuthTokenResponse)
async def issue_token(payload: AuthTokenRequest, request: Request) -> AuthTokenResponse:
    settings = request.app.state.settings
    if payload.client_id != settings.dummy_oauth_client_id or payload.client_secret != settings.dummy_oauth_client_secret:
        raise HTTPException(status_code=401, detail="invalid client credentials")
    token, _exp = issue_jwt(settings.jwt_secret, settings.jwt_issuer, settings.jwt_ttl_seconds, payload.client_id)
    return AuthTokenResponse(access_token=token, expires_in=settings.jwt_ttl_seconds)

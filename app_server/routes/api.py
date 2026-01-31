from __future__ import annotations

from typing import Any

import time

from fastapi import APIRouter, Depends, HTTPException, Request

from auth.jwt import verify_jwt
from providers import gemini, google_calendar
from shared.utils import extract_bearer_token

router = APIRouter(prefix="/api")


def require_jwt(request: Request) -> dict[str, Any]:
    token = extract_bearer_token(request.headers.get("authorization"))
    if not token:
        raise HTTPException(status_code=401, detail="missing bearer token")
    settings = request.app.state.settings
    try:
        return verify_jwt(token, settings.jwt_secret, settings.jwt_issuer)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc


async def _get_token(conn, settings, credential_id: str):
    row = conn.execute(
        "SELECT access_token, refresh_token, expiry FROM oauth_tokens WHERE credential_id = ?",
        (credential_id,),
    ).fetchone()
    if not row:
        return None
    if row["expiry"] and row["refresh_token"]:
        now = int(time.time())
        if now >= int(row["expiry"]) - 60:
            payload = await google_calendar.refresh_access_token(
                row["refresh_token"],
                settings.google_client_id,
                settings.google_client_secret,
            )
            access_token = payload.get("access_token")
            expires_in = int(payload.get("expires_in", 0))
            expiry = now + expires_in if expires_in else None
            conn.execute(
                "UPDATE oauth_tokens SET access_token = ?, expiry = ?, updated_at = ? WHERE credential_id = ?",
                (access_token, expiry, now, credential_id),
            )
            conn.commit()
            return {"access_token": access_token, "refresh_token": row["refresh_token"], "expiry": expiry}
    return row


@router.get("/google_calendar/{credential_id}/list_calendars")
async def list_calendars(request: Request, credential_id: str, _jwt=Depends(require_jwt)):
    token_row = await _get_token(request.app.state.db, request.app.state.settings, credential_id)
    if not token_row:
        raise HTTPException(status_code=404, detail="token not found")
    return await google_calendar.list_calendars(token_row["access_token"])


@router.get("/google_calendar/{credential_id}/list_events")
async def list_events(
    request: Request,
    credential_id: str,
    calendar_id: str,
    max_results: int | None = None,
    time_min: str | None = None,
    order_by: str | None = None,
    single_events: bool | None = None,
    _jwt=Depends(require_jwt),
):
    token_row = await _get_token(request.app.state.db, request.app.state.settings, credential_id)
    if not token_row:
        raise HTTPException(status_code=404, detail="token not found")
    return await google_calendar.list_events(
        token_row["access_token"],
        calendar_id,
        max_results=max_results,
        time_min=time_min,
        order_by=order_by,
        single_events=single_events,
    )


@router.post("/google_calendar/{credential_id}/create_event")
async def create_event(
    request: Request,
    credential_id: str,
    payload: dict,
    _jwt=Depends(require_jwt),
):
    token_row = await _get_token(request.app.state.db, request.app.state.settings, credential_id)
    if not token_row:
        raise HTTPException(status_code=404, detail="token not found")
    try:
        return await google_calendar.create_event(token_row["access_token"], payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/gemini/{credential_id}/generate")
async def gemini_generate(
    request: Request,
    credential_id: str,
    payload: dict,
    _jwt=Depends(require_jwt),
):
    settings = request.app.state.settings
    token_row = _get_token(request.app.state.db, credential_id)
    api_key = token_row["access_token"] if token_row and token_row["access_token"] else settings.gemini_api_key
    return await gemini.generate(api_key, settings.gemini_base_url, settings.gemini_model, payload)

from __future__ import annotations

import httpx

BASE_URL = "https://www.googleapis.com/calendar/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def _auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


async def list_calendars(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BASE_URL}/users/me/calendarList", headers=_auth_headers(access_token))
    resp.raise_for_status()
    return resp.json()


async def list_events(
    access_token: str,
    calendar_id: str,
    max_results: int | None = None,
    time_min: str | None = None,
    order_by: str | None = None,
    single_events: bool | None = None,
) -> dict:
    params = {}
    if max_results is not None:
        params["maxResults"] = max_results
    if time_min:
        params["timeMin"] = time_min
    if order_by:
        params["orderBy"] = order_by
    if single_events is not None:
        params["singleEvents"] = str(single_events).lower()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{BASE_URL}/calendars/{calendar_id}/events",
            headers=_auth_headers(access_token),
            params=params or None,
        )
    resp.raise_for_status()
    return resp.json()


async def create_event(access_token: str, payload: dict) -> dict:
    calendar_id = payload.get("calendar_id")
    if not calendar_id:
        raise ValueError("calendar_id required")
    body = payload.get("event") or payload
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{BASE_URL}/calendars/{calendar_id}/events",
            headers=_auth_headers(access_token),
            json=body,
        )
    resp.raise_for_status()
    return resp.json()


async def refresh_access_token(refresh_token: str, client_id: str, client_secret: str) -> dict:
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(TOKEN_URL, data=data)
    resp.raise_for_status()
    return resp.json()

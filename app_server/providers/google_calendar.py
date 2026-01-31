from __future__ import annotations

import httpx

BASE_URL = "https://www.googleapis.com/calendar/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def _auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


async def list_calendars(
    access_token: str,
    max_results: int | None = None,
    page_token: str | None = None,
    min_access_role: str | None = None,
    fields: str | None = None,
) -> dict:
    params = {}
    if max_results is not None:
        params["maxResults"] = max_results
    if page_token:
        params["pageToken"] = page_token
    if min_access_role:
        params["minAccessRole"] = min_access_role
    if fields:
        params["fields"] = fields
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{BASE_URL}/users/me/calendarList",
            headers=_auth_headers(access_token),
            params=params or None,
        )
    resp.raise_for_status()
    return resp.json()


async def list_events(
    access_token: str,
    calendar_id: str,
    max_results: int | None = None,
    page_token: str | None = None,
    time_min: str | None = None,
    time_max: str | None = None,
    order_by: str | None = None,
    single_events: bool | None = None,
    q: str | None = None,
    show_deleted: bool | None = None,
    time_zone: str | None = None,
    fields: str | None = None,
) -> dict:
    params = {}
    if max_results is not None:
        params["maxResults"] = max_results
    if page_token:
        params["pageToken"] = page_token
    if time_min:
        params["timeMin"] = time_min
    if time_max:
        params["timeMax"] = time_max
    if order_by:
        params["orderBy"] = order_by
    if single_events is not None:
        params["singleEvents"] = str(single_events).lower()
    if q:
        params["q"] = q
    if show_deleted is not None:
        params["showDeleted"] = str(show_deleted).lower()
    if time_zone:
        params["timeZone"] = time_zone
    if fields:
        params["fields"] = fields
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{BASE_URL}/calendars/{calendar_id}/events",
            headers=_auth_headers(access_token),
            params=params or None,
        )
    resp.raise_for_status()
    return resp.json()


async def get_event(access_token: str, calendar_id: str, event_id: str, fields: str | None = None) -> dict:
    params = {"fields": fields} if fields else None
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{BASE_URL}/calendars/{calendar_id}/events/{event_id}",
            headers=_auth_headers(access_token),
            params=params,
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


async def update_event(access_token: str, calendar_id: str, event_id: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(
            f"{BASE_URL}/calendars/{calendar_id}/events/{event_id}",
            headers=_auth_headers(access_token),
            json=payload,
        )
    resp.raise_for_status()
    return resp.json()


async def delete_event(access_token: str, calendar_id: str, event_id: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{BASE_URL}/calendars/{calendar_id}/events/{event_id}",
            headers=_auth_headers(access_token),
        )
    resp.raise_for_status()
    return {"deleted": True}


async def availability(access_token: str, calendar_id: str, time_min: str, time_max: str, time_zone: str | None = None) -> dict:
    body = {
        "timeMin": time_min,
        "timeMax": time_max,
        "items": [{"id": calendar_id}],
    }
    if time_zone:
        body["timeZone"] = time_zone
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{BASE_URL}/freeBusy",
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

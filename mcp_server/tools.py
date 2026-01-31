from __future__ import annotations

from typing import Any

from auth import require_jwt
from client import get, post


async def gcal_list_calendars(
    app_server_url: str,
    credential_id: str,
    jwt: str,
    max_results: int | None = None,
    page_token: str | None = None,
    min_access_role: str | None = None,
    fields: str | None = None,
) -> dict:
    jwt = require_jwt(jwt)
    return await get(
        app_server_url,
        f"/api/google_calendar/{credential_id}/list_calendars",
        jwt,
        params={
            "max_results": max_results,
            "page_token": page_token,
            "min_access_role": min_access_role,
            "fields": fields,
        },
    )


async def gcal_list_events(
    app_server_url: str,
    credential_id: str,
    calendar_id: str,
    jwt: str,
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
    jwt = require_jwt(jwt)
    return await get(
        app_server_url,
        f"/api/google_calendar/{credential_id}/list_events",
        jwt,
        params={
            "calendar_id": calendar_id,
            "max_results": max_results,
            "page_token": page_token,
            "time_min": time_min,
            "time_max": time_max,
            "order_by": order_by,
            "single_events": single_events,
            "q": q,
            "show_deleted": show_deleted,
            "time_zone": time_zone,
            "fields": fields,
        },
    )


async def gcal_create_event(
    app_server_url: str, credential_id: str, payload: dict, jwt: str
) -> dict:
    jwt = require_jwt(jwt)
    return await post(
        app_server_url,
        f"/api/google_calendar/{credential_id}/create_event",
        jwt,
        payload,
    )


async def gcal_get_event(
    app_server_url: str,
    credential_id: str,
    calendar_id: str,
    event_id: str,
    jwt: str,
    fields: str | None = None,
) -> dict:
    jwt = require_jwt(jwt)
    return await get(
        app_server_url,
        f"/api/google_calendar/{credential_id}/get_event",
        jwt,
        params={"calendar_id": calendar_id, "event_id": event_id, "fields": fields},
    )


async def gcal_update_event(
    app_server_url: str,
    credential_id: str,
    calendar_id: str,
    event_id: str,
    payload: dict,
    jwt: str,
) -> dict:
    jwt = require_jwt(jwt)
    return await post(
        app_server_url,
        f"/api/google_calendar/{credential_id}/update_event",
        jwt,
        {"calendar_id": calendar_id, "event_id": event_id, **payload},
    )


async def gcal_delete_event(
    app_server_url: str,
    credential_id: str,
    calendar_id: str,
    event_id: str,
    jwt: str,
) -> dict:
    jwt = require_jwt(jwt)
    return await post(
        app_server_url,
        f"/api/google_calendar/{credential_id}/delete_event",
        jwt,
        {"calendar_id": calendar_id, "event_id": event_id},
    )


async def gcal_availability(
    app_server_url: str,
    credential_id: str,
    calendar_id: str,
    time_min: str,
    time_max: str,
    jwt: str,
    time_zone: str | None = None,
) -> dict:
    jwt = require_jwt(jwt)
    return await post(
        app_server_url,
        f"/api/google_calendar/{credential_id}/availability",
        jwt,
        {
            "calendar_id": calendar_id,
            "time_min": time_min,
            "time_max": time_max,
            "time_zone": time_zone,
        },
    )


async def gemini_generate(
    app_server_url: str, credential_id: str, prompt: str, jwt: str
) -> dict:
    jwt = require_jwt(jwt)
    payload = {"prompt": prompt}
    return await post(
        app_server_url, f"/api/gemini/{credential_id}/generate", jwt, payload
    )

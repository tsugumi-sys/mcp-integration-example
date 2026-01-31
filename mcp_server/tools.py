from __future__ import annotations

from typing import Any

from auth import require_jwt
from client import get, post


async def gcal_list_calendars(app_server_url: str, credential_id: str, jwt: str) -> dict:
    jwt = require_jwt(jwt)
    return await get(app_server_url, f"/api/google_calendar/{credential_id}/list_calendars", jwt)


async def gcal_list_events(
    app_server_url: str,
    credential_id: str,
    calendar_id: str,
    jwt: str,
    max_results: int | None = None,
    time_min: str | None = None,
    order_by: str | None = None,
    single_events: bool | None = None,
) -> dict:
    jwt = require_jwt(jwt)
    return await get(
        app_server_url,
        f"/api/google_calendar/{credential_id}/list_events",
        jwt,
        params={
            "calendar_id": calendar_id,
            "max_results": max_results,
            "time_min": time_min,
            "order_by": order_by,
            "single_events": single_events,
        },
    )


async def gcal_create_event(app_server_url: str, credential_id: str, payload: dict, jwt: str) -> dict:
    jwt = require_jwt(jwt)
    return await post(
        app_server_url,
        f"/api/google_calendar/{credential_id}/create_event",
        jwt,
        payload,
    )


async def gemini_generate(app_server_url: str, credential_id: str, prompt: str, jwt: str) -> dict:
    jwt = require_jwt(jwt)
    payload = {"prompt": prompt}
    return await post(app_server_url, f"/api/gemini/{credential_id}/generate", jwt, payload)

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastmcp import FastMCP

import tools

load_dotenv()
APP_SERVER_URL = os.getenv("APP_SERVER_URL", "http://127.0.0.1:8000")
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "9001"))

mcp = FastMCP("mcp-server")


@mcp.tool(name="gcal.list_calendars")
async def gcal_list_calendars(
    credential_id: str,
    jwt: str,
    max_results: int | None = None,
    page_token: str | None = None,
    min_access_role: str | None = None,
    fields: str | None = None,
):
    return await tools.gcal_list_calendars(
        APP_SERVER_URL,
        credential_id,
        jwt,
        max_results=max_results,
        page_token=page_token,
        min_access_role=min_access_role,
        fields=fields,
    )


@mcp.tool(name="gcal.list_events")
async def gcal_list_events(
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
):
    return await tools.gcal_list_events(
        APP_SERVER_URL,
        credential_id,
        calendar_id,
        jwt,
        max_results=max_results,
        page_token=page_token,
        time_min=time_min,
        time_max=time_max,
        order_by=order_by,
        single_events=single_events,
        q=q,
        show_deleted=show_deleted,
        time_zone=time_zone,
        fields=fields,
    )


@mcp.tool(name="gcal.create_event")
async def gcal_create_event(credential_id: str, payload: dict, jwt: str):
    return await tools.gcal_create_event(APP_SERVER_URL, credential_id, payload, jwt)


@mcp.tool(name="gcal.get_event")
async def gcal_get_event(credential_id: str, calendar_id: str, event_id: str, jwt: str, fields: str | None = None):
    return await tools.gcal_get_event(APP_SERVER_URL, credential_id, calendar_id, event_id, jwt, fields=fields)


@mcp.tool(name="gcal.update_event")
async def gcal_update_event(
    credential_id: str, calendar_id: str, event_id: str, payload: dict, jwt: str
):
    return await tools.gcal_update_event(APP_SERVER_URL, credential_id, calendar_id, event_id, payload, jwt)


@mcp.tool(name="gcal.delete_event")
async def gcal_delete_event(credential_id: str, calendar_id: str, event_id: str, jwt: str):
    return await tools.gcal_delete_event(APP_SERVER_URL, credential_id, calendar_id, event_id, jwt)


@mcp.tool(name="gcal.availability")
async def gcal_availability(
    credential_id: str, calendar_id: str, time_min: str, time_max: str, jwt: str, time_zone: str | None = None
):
    return await tools.gcal_availability(
        APP_SERVER_URL,
        credential_id,
        calendar_id,
        time_min,
        time_max,
        jwt,
        time_zone=time_zone,
    )


@mcp.tool(name="gemini.generate")
async def gemini_generate(credential_id: str, prompt: str, jwt: str):
    return await tools.gemini_generate(APP_SERVER_URL, credential_id, prompt, jwt)


def main() -> None:
    mcp.run(transport="http", host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    main()

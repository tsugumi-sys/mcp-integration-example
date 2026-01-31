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
async def gcal_list_calendars(credential_id: str, jwt: str):
    return await tools.gcal_list_calendars(APP_SERVER_URL, credential_id, jwt)


@mcp.tool(name="gcal.list_events")
async def gcal_list_events(credential_id: str, calendar_id: str, jwt: str):
    return await tools.gcal_list_events(APP_SERVER_URL, credential_id, calendar_id, jwt)


@mcp.tool(name="gcal.create_event")
async def gcal_create_event(credential_id: str, payload: dict, jwt: str):
    return await tools.gcal_create_event(APP_SERVER_URL, credential_id, payload, jwt)


@mcp.tool(name="gemini.generate")
async def gemini_generate(credential_id: str, prompt: str, jwt: str):
    return await tools.gemini_generate(APP_SERVER_URL, credential_id, prompt, jwt)


def main() -> None:
    mcp.run(transport="http", host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    main()

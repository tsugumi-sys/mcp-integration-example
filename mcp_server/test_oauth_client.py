from __future__ import annotations

import os

import anyio
from fastmcp import Client


MCP_URL = "http://127.0.0.1:9001/mcp"
DEFAULT_GOOGLE_CREDENTIAL_ID = "2bdeef18-2c7f-46e0-a11a-c3eebdf6fa9b"


async def main() -> None:
    async with Client(MCP_URL, auth="oauth") as client:
        tools = await client.list_tools()
        print("Connected to MCP server.")
        print("Available tools:")
        for tool in tools:
            print(f"- {tool.name}")

        credential_id = os.getenv(
            "TEST_GOOGLE_CREDENTIAL_ID", DEFAULT_GOOGLE_CREDENTIAL_ID
        )
        result = await client.call_tool(
            "gcal.list_calendars",
            {"credential_id": credential_id, "max_results": 10},
        )
        print("\nCalendar result:")
        print(result)


if __name__ == "__main__":
    anyio.run(main)

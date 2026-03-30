# mcp_server

## Run
- `uv run main.py`

## Environment
`python-dotenv` を使って `.env` を読み込みます。

Optional (defaults)
- `APP_SERVER_URL` (http://127.0.0.1:8000)
- `MCP_HOST` (127.0.0.1)
- `MCP_PORT` (9001)

## HTTP Endpoint
- Default URL: `http://127.0.0.1:9001/mcp`

## Auth
- MCP tools no longer take a `jwt` argument.
- The server expects bearer auth on the MCP HTTP connection and forwards that token to `app_server`.
- For local in-app chat, the app connects with `fastmcp.Client(..., auth=<jwt>)`.
- For external clients such as Claude Desktop, use the app server OAuth endpoints to obtain a bearer token and then connect to the MCP endpoint with that token.

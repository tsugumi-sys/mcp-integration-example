# MCP Example

## Architecture

![Architecture](architecture.png)

## Claude Desktop Test

This repo can be tested from Claude Desktop against the local remote MCP endpoint.

Prerequisites:

- Claude Desktop with remote MCP connectors enabled
- a Claude plan that supports custom remote MCP connectors
- `app_server` and `mcp_server` running locally
- Google admin login configured
- at least one connected Google Calendar credential in the admin UI

Start servers:

1. In one terminal:
```bash
cd app_server
uv run main.py
```
2. In another terminal:
```bash
cd mcp_server
uv run main.py
```

Default local URLs:

- App Server: `http://127.0.0.1:8000`
- MCP Server: `http://127.0.0.1:9001/mcp`

Recommended pre-checks:

1. Open `http://127.0.0.1:8000/auth/login` and confirm Google login works.
2. Open `http://127.0.0.1:8000/credentials` and confirm the target Google Calendar credential is `connected`.
3. Open `http://127.0.0.1:8000/.well-known/oauth-authorization-server` and confirm metadata is returned.

Claude Desktop steps:

1. Open Claude Desktop.
2. Go to `Settings > Connectors`.
3. Add a custom remote connector.
4. Enter the MCP URL:
   `http://127.0.0.1:9001/mcp`
5. Start the connector auth flow when Claude Desktop prompts for authentication.
6. Complete the OAuth flow in the browser:
   - client registration is handled by Claude Desktop
   - login is handled by this app at `http://127.0.0.1:8000/auth/login`
   - authorization is handled by this app at `http://127.0.0.1:8000/oauth/authorize`
7. Return to Claude Desktop and confirm the connector shows as connected.

Suggested smoke tests in Claude Desktop:

1. Ask Claude to list available calendars.
2. Ask Claude to list events for a selected calendar.
3. Ask Claude to create a small test event in that calendar.

Expected behavior:

- Claude Desktop connects to the local MCP endpoint over HTTP
- bearer auth is sent on the MCP connection
- `mcp_server` forwards that bearer token to `app_server`
- `app_server` validates the JWT and executes the Google Calendar API call

Notes:

- The local in-app chat and Claude Desktop can coexist. They use the same MCP tool surface, but they obtain bearer tokens through different client paths.
- The in-app chat is an internal client and still issues JWTs directly inside `app_server`.
- Claude Desktop is an external client and uses OAuth metadata, registration, authorization, and token exchange.
- If you see JWT warnings locally, set a long random `JWT_SECRET` in `app_server/.env`.

## Tool Selection Control

- MCPサーバーは複数ツールを持つが、**実際にLLMへ渡すツールはルーム設定で限定**される。
- ユーザー（またはエージェント）が「使いたい統合だけ」を選べる設計なので、冗長な全ツール渡しは行わない。
- 将来ワークフロー拡張する場合も、**同一MCP内のツール群から必要なものだけ選択**できる。

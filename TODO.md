# TODO (Phase 1)

## 1. Project Setup
- [ ] Add basic project layout (`app_server/`, `mcp_server/`, `data/`)
- [ ] Add `pyproject.toml` and uv config
- [ ] Add `.env.example`

## 2. App Server (FastAPI)
### Core
- [ ] `app_server/main.py` entrypoint
- [ ] `app_server/config.py` for env loading
- [ ] `app_server/db.py` for sqlite connect + schema init

### Admin UI + Auth
- [ ] Dummy OAuth provider (authorize/token/callback)
- [ ] Admin UI session handling (cookie)
- [ ] Routes: login/logout, credentials list/detail/create/delete

### OAuth (Google Calendar)
- [ ] OAuth start endpoint (save state)
- [ ] OAuth callback (code exchange → token save)
- [ ] Token refresh logic

### Providers
- [ ] Google Calendar executor (list calendars/events, create event)
- [ ] Gemini API call logic (minimal)

### Backend API
- [ ] `/auth/token` JWT issuance (client credentials)
- [ ] `/api/{provider}/{credential_id}/...` routing
- [ ] JWT validation middleware

## 3. MCP Server (fastmcp)
- [ ] MCP server entrypoint
- [ ] Tool definitions (`gcal.*`)
- [ ] App Server client (JWT passthrough)
- [ ] Reject connections without JWT

## 4. App Server Local Types
- [ ] App server DTOs / error shapes
- [ ] Provider enums

## 5. UI / Templates
- [ ] `base.html`, `credentials.html`, `credential_detail.html`
- [ ] Minimal CSS

## 6. Local Dev
- [ ] Seed DB or create initial credential flow
- [ ] README or notes for running (uv run)

## 7. Smoke Tests
- [ ] OAuth flow (dummy + google)
- [ ] JWT issuance + MCP call
- [ ] Gemini API call (happy path)

# TODO

This file tracks the concrete implementation work derived from `Plan.md`.

## Current focus

- [ ] Replace admin Dummy OAuth login with Google Sign-In
- [ ] Add OAuth authorization server metadata and dynamic client registration
- [ ] Support authorization-code token issuance for registered MCP clients
- [ ] Verify the localhost MCP endpoint from Claude Desktop

## Completed baseline already in repo

- [x] App Server basic structure exists
- [x] MCP Server basic structure exists
- [x] SQLite schema for credentials, oauth tokens, oauth state, admin sessions, and chat exists
- [x] Admin session cookie flow exists
- [x] Google Calendar provider OAuth exists
- [x] JWT issuance and verification path exists
- [x] Chat UI and MCP tool forwarding exist

## Phase 1: Google Sign-In for admin UI

### Config
- [x] Add Google login env vars in `app_server/config.py`
- [ ] Decide admin access policy: explicit allowlist or Google Workspace domain
- [x] Update `app_server/README.md` with Google login setup steps

### Routes and login flow
- [x] Add `app_server/routes/google_login.py`
- [x] Implement `GET /auth/login` for Google login start
- [x] Implement Google callback handling
- [x] Validate Google identity claims and enforce admin access policy
- [x] Reuse `admin_sessions` for successful login
- [ ] Keep `POST /auth/logout` working with the existing session cookie

### Cleanup
- [x] Remove Dummy OAuth from the default admin login path
- [ ] Decide whether Dummy OAuth remains behind a dev-only flag or is removed

## Phase 2: OAuth authorization server metadata and client registry

### Protocol surface
- [ ] Confirm the exact MCP/FastMCP remote auth requirements this repo needs to satisfy
- [x] Define the metadata document shape before coding endpoints

### DB
- [x] Add `oauth_clients` table in `app_server/db.py`
- [x] Store client metadata: redirect URIs, grant types, response types, scopes, auth method

### Routes
- [x] Add metadata route module
- [x] Implement `GET /.well-known/oauth-authorization-server`
- [ ] Add optional OIDC metadata endpoint only if needed by the client

### Existing token path cleanup
- [x] Stop using `dummy_oauth_client_id` and `dummy_oauth_client_secret` as the production token gate
- [ ] Keep a dev-only shortcut only if still necessary

## Phase 3: Dynamic client registration

### Registration endpoint
- [x] Add registration route module
- [x] Implement `POST /oauth/register`

### Validation and persistence
- [x] Validate redirect URIs
- [x] Validate grant types
- [x] Validate token endpoint auth method
- [x] Generate and persist `client_id`
- [x] Generate and persist `client_secret` when required

### Response shape
- [x] Return registration response fields needed by clients
- [x] Add clear error responses for unsupported registration requests

## Phase 4: Authorization code flow for registered clients

### Authorization endpoint
- [x] Add authorization route module
- [x] Implement `GET /oauth/authorize`
- [x] Validate `client_id`, `redirect_uri`, `response_type`, `state`, and scopes

### Session-aware approval flow
- [x] Redirect unauthenticated users through Google login
- [x] Resume the OAuth authorization flow after login
- [x] Auto-approve for the logged-in admin in Phase 1 unless explicit consent UI is needed

### DB
- [x] Add `oauth_authorization_codes` table in `app_server/db.py`
- [x] Store authorization code, client, redirect URI, subject, scope, and expiry

### Token endpoint
- [x] Extend the token endpoint to exchange authorization codes for JWT access tokens
- [x] Validate client authentication
- [x] Validate code ownership, expiry, and redirect URI match
- [x] Decide and implement the JWT subject model

## Phase 5: MCP integration cleanup

### MCP server
- [ ] Revisit whether `jwt` should remain an explicit MCP tool argument
- [ ] Align `mcp_server` auth behavior with the new authorization server flow

### App chat integration
- [ ] Review `app_server/routes/chat.py` JWT injection behavior
- [ ] Keep or refactor the local chat shortcut intentionally instead of leaving it as a hidden assumption

### Docs
- [ ] Update root `README.md`
- [ ] Update `docs/ARCHITECTURE.md`
- [ ] Document the Claude Desktop localhost test flow

## Verification

- [ ] Manual test: Google Sign-In can create an admin session
- [ ] Manual test: registered client can discover metadata
- [ ] Manual test: registered client can dynamically register
- [ ] Manual test: registered client can complete authorization-code flow
- [ ] Manual test: issued JWT can call protected app endpoints
- [ ] Manual test: Claude Desktop can connect to the localhost MCP endpoint successfully

# app_server

## Run
- `uv run main.py`

## First Access
- Open `http://127.0.0.1:8000/auth/login` and sign in with any email.
- After login, you will be redirected to `/credentials`.
- Chat UI is at `/chat`.

## Gemini API Key (UI)
- Create a credential with provider `gemini`.
- Open the credential detail and register your API key.
- The saved key is stored in the DB and used for Gemini calls.

## Environment
`python-dotenv` を使って `.env` を読み込みます。

Required
- `JWT_SECRET`

Optional (defaults)
- `APP_HOST` (127.0.0.1)
- `APP_PORT` (8000)
- `DATABASE_PATH` (./data/app.db)
- `JWT_ISSUER` (app-server)
- `JWT_TTL_SECONDS` (900)
- `ADMIN_SESSION_TTL_SECONDS` (3600)
- `DUMMY_OAUTH_CLIENT_ID` (dummy-client)
- `DUMMY_OAUTH_CLIENT_SECRET` (dummy-secret)
- `GOOGLE_CLIENT_ID` (empty)
- `GOOGLE_CLIENT_SECRET` (empty)
- `GEMINI_BASE_URL` (https://generativelanguage.googleapis.com/v1beta)
- `GEMINI_MODEL` (gemini-3-flash-preview)
- `MCP_SERVER_URL` (http://127.0.0.1:9001/mcp)

## Google OAuth client setup (local dev)
- Create a **Web application** OAuth client.
- Add this redirect URI exactly:
  `http://127.0.0.1:8000/oauth/google_calendar/callback`
- Enable Google Calendar API in the project.

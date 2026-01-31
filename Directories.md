# Directory Structure (Phase1)

```
.
├─ app_server/
│  ├─ main.py                 # FastAPI entry
│  ├─ config.py               # settings/env
│  ├─ db.py                   # sqlite connection/migrations
│  ├─ data/
│  │  └─ app.db                # sqlite file (local dev)
│  ├─ shared/
│  │  ├─ models.py             # local DTOs/types
│  │  └─ utils.py              # common helpers
│  ├─ auth/
│  │  ├─ jwt.py                # JWT issue/verify
│  │  ├─ session.py            # Admin UI session
│  │  └─ dummy_oauth.py         # dummy oauth provider
│  ├─ routes/
│  │  ├─ admin.py              # admin UI pages
│  │  ├─ oauth.py              # provider oauth callbacks
│  │  ├─ dummy_oauth.py         # dummy oauth endpoints
│  │  ├─ auth.py               # /auth/token
│  │  └─ api.py                # /api/{provider}/...
│  ├─ providers/
│  │  ├─ google_calendar.py    # gcal executor
│  │  └─ gemini.py             # gemini call logic
│  ├─ templates/
│  │  ├─ base.html
│  │  ├─ credentials.html
│  │  └─ credential_detail.html
│  └─ static/
│     └─ style.css
│
├─ mcp_server/
│  ├─ main.py                 # fastmcp entry
│  ├─ tools.py                # tool definitions
│  ├─ client.py               # app server client
│  └─ auth.py                 # JWT passthrough/validation
│
├─ DESIGN.md
└─ Directories.md
```

Notes
- `app_server/auth/dummy_oauth.py` holds the minimal dummy provider logic; UI routes live in `app_server/routes/dummy_oauth.py`.
- `mcp_server/auth.py` only validates presence/shape of JWT and forwards it; it does not store tokens.
- `providers/gemini.py` is the real Gemini API call logic (Phase1 required).
- `app_server/shared/` is local to the app server. MCP is fully separated in Phase1.

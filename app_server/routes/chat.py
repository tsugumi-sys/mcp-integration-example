from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

import json

from auth.session import get_session
from auth.jwt import issue_jwt
from fastmcp import Client
from providers import gemini

router = APIRouter(prefix="/chat")
TEMPLATES = Jinja2Templates(directory="templates")
COOKIE_NAME = "admin_session"


def require_session(request: Request):
    session_id = request.cookies.get(COOKIE_NAME)
    if not session_id:
        raise HTTPException(status_code=302, headers={"Location": "/auth/login"})
    session = get_session(request.app.state.db, session_id)
    if not session:
        raise HTTPException(status_code=302, headers={"Location": "/auth/login"})
    return session


def _fetch_credentials(conn, provider: str):
    return conn.execute(
        "SELECT id, name, status FROM credentials WHERE provider = ? ORDER BY created_at DESC",
        (provider,),
    ).fetchall()


def _get_token(conn, credential_id: str):
    row = conn.execute(
        "SELECT access_token FROM oauth_tokens WHERE credential_id = ?",
        (credential_id,),
    ).fetchone()
    return row["access_token"] if row and row["access_token"] else None


def _build_tools(providers: list[dict]) -> list[dict]:
    declarations = []
    for provider in providers:
        if provider["provider"] == "google_calendar":
            declarations.extend(
                [
                    {
                        "name": "gcal.list_calendars",
                        "description": "List calendars for the user",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "credential_id": {"type": "string"},
                                "max_results": {"type": "integer"},
                                "page_token": {"type": "string"},
                                "min_access_role": {"type": "string"},
                                "fields": {"type": "string"},
                                "jwt": {"type": "string"},
                            },
                            "required": ["credential_id", "jwt"],
                        },
                    },
                    {
                        "name": "gcal.list_events",
                        "description": "List events in a calendar",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "credential_id": {"type": "string"},
                                "calendar_id": {"type": "string"},
                                "max_results": {"type": "integer"},
                                "page_token": {"type": "string"},
                                "time_min": {"type": "string"},
                                "time_max": {"type": "string"},
                                "order_by": {"type": "string"},
                                "single_events": {"type": "boolean"},
                                "q": {"type": "string"},
                                "show_deleted": {"type": "boolean"},
                                "time_zone": {"type": "string"},
                                "fields": {"type": "string"},
                                "jwt": {"type": "string"},
                            },
                            "required": ["credential_id", "calendar_id", "jwt"],
                        },
                    },
                    {
                        "name": "gcal.get_event",
                        "description": "Get a single event",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "credential_id": {"type": "string"},
                                "calendar_id": {"type": "string"},
                                "event_id": {"type": "string"},
                                "fields": {"type": "string"},
                                "jwt": {"type": "string"},
                            },
                            "required": ["credential_id", "calendar_id", "event_id", "jwt"],
                        },
                    },
                    {
                        "name": "gcal.create_event",
                        "description": "Create an event",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "credential_id": {"type": "string"},
                                "calendar_id": {"type": "string"},
                                "event": {"type": "object"},
                                "jwt": {"type": "string"},
                            },
                            "required": ["credential_id", "calendar_id", "event", "jwt"],
                        },
                    },
                    {
                        "name": "gcal.update_event",
                        "description": "Update an event",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "credential_id": {"type": "string"},
                                "calendar_id": {"type": "string"},
                                "event_id": {"type": "string"},
                                "payload": {"type": "object"},
                                "jwt": {"type": "string"},
                            },
                            "required": ["credential_id", "calendar_id", "event_id", "payload", "jwt"],
                        },
                    },
                    {
                        "name": "gcal.delete_event",
                        "description": "Delete an event",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "credential_id": {"type": "string"},
                                "calendar_id": {"type": "string"},
                                "event_id": {"type": "string"},
                                "jwt": {"type": "string"},
                            },
                            "required": ["credential_id", "calendar_id", "event_id", "jwt"],
                        },
                    },
                    {
                        "name": "gcal.availability",
                        "description": "Check free/busy for a time range",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "credential_id": {"type": "string"},
                                "calendar_id": {"type": "string"},
                                "time_min": {"type": "string"},
                                "time_max": {"type": "string"},
                                "time_zone": {"type": "string"},
                                "jwt": {"type": "string"},
                            },
                            "required": ["credential_id", "calendar_id", "time_min", "time_max", "jwt"],
                        },
                    },
                ]
            )
    if not declarations:
        return []
    return [{"functionDeclarations": declarations}]


def _make_jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {k: _make_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_jsonable(v) for v in value]
    if hasattr(value, "model_dump"):
        return _make_jsonable(value.model_dump())
    if hasattr(value, "dict"):
        return _make_jsonable(value.dict())
    if hasattr(value, "__dict__"):
        return _make_jsonable(value.__dict__)
    try:
        return json.loads(json.dumps(value))
    except Exception:
        return str(value)


@router.get("")
async def chat_list(request: Request, session=Depends(require_session)):
    rooms = request.app.state.db.execute(
        "SELECT id, name, llm_provider, created_at FROM chat_rooms ORDER BY created_at DESC"
    ).fetchall()
    room_providers = {}
    for room in rooms:
        providers = request.app.state.db.execute(
            "SELECT provider FROM chat_room_providers WHERE room_id = ? ORDER BY provider",
            (room["id"],),
        ).fetchall()
        room_providers[room["id"]] = [row["provider"] for row in providers]
    gemini_credentials = _fetch_credentials(request.app.state.db, "gemini")
    gcal_credentials = _fetch_credentials(request.app.state.db, "google_calendar")
    return TEMPLATES.TemplateResponse(
        "chat_list.html",
        {
            "request": request,
            "rooms": rooms,
            "room_providers": room_providers,
            "session": session,
            "gemini_credentials": gemini_credentials,
            "gcal_credentials": gcal_credentials,
        },
    )


@router.post("")
async def chat_create(
    request: Request,
    name: str = Form(""),
    llm_provider: str = Form("gemini"),
    llm_credential_id: str = Form(""),
    mcp_providers: list[str] = Form([]),
    mcp_credential_google_calendar: str = Form(""),
    session=Depends(require_session),
):
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    room_id = str(uuid.uuid4())
    now = int(time.time())
    request.app.state.db.execute(
        "INSERT INTO chat_rooms (id, name, llm_provider, llm_credential_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (room_id, name, llm_provider, llm_credential_id or None, now),
    )
    for provider in mcp_providers:
        credential_id = None
        if provider == "google_calendar":
            credential_id = mcp_credential_google_calendar or None
        request.app.state.db.execute(
            "INSERT OR REPLACE INTO chat_room_providers (room_id, provider, credential_id, created_at) VALUES (?, ?, ?, ?)",
            (room_id, provider, credential_id, now),
        )
    request.app.state.db.commit()
    return RedirectResponse(f"/chat/{room_id}", status_code=302)


@router.get("/{room_id}")
async def chat_room(request: Request, room_id: str, session=Depends(require_session)):
    room = request.app.state.db.execute(
        "SELECT * FROM chat_rooms WHERE id = ?",
        (room_id,),
    ).fetchone()
    if not room:
        raise HTTPException(status_code=404, detail="room not found")
    providers = request.app.state.db.execute(
        "SELECT provider, credential_id FROM chat_room_providers WHERE room_id = ? ORDER BY provider",
        (room_id,),
    ).fetchall()
    messages = request.app.state.db.execute(
        "SELECT role, content, created_at FROM chat_messages WHERE room_id = ? ORDER BY created_at ASC",
        (room_id,),
    ).fetchall()
    return TEMPLATES.TemplateResponse(
        "chat_room.html",
        {"request": request, "room": room, "providers": providers, "messages": messages, "session": session},
    )


@router.post("/{room_id}/message")
async def chat_message(
    request: Request,
    room_id: str,
    prompt: str = Form(""),
    session=Depends(require_session),
):
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt required")

    conn = request.app.state.db
    room = conn.execute("SELECT * FROM chat_rooms WHERE id = ?", (room_id,)).fetchone()
    if not room:
        raise HTTPException(status_code=404, detail="room not found")
    providers = conn.execute(
        "SELECT provider, credential_id FROM chat_room_providers WHERE room_id = ? ORDER BY provider",
        (room_id,),
    ).fetchall()
    credential_map = {row["provider"]: row["credential_id"] for row in providers}

    now = int(time.time())
    user_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO chat_messages (id, room_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, room_id, "user", prompt, now),
    )

    tool_note = ""
    settings = request.app.state.settings
    jwt, _exp = issue_jwt(settings.jwt_secret, settings.jwt_issuer, settings.jwt_ttl_seconds, "app-server")
    tools = _build_tools(providers)

    llm_text = ""
    if room["llm_provider"] == "gemini":
        api_key = None
        if room["llm_credential_id"]:
            api_key = _get_token(conn, room["llm_credential_id"])
        response = await gemini.generate_with_tools(
            api_key,
            settings.gemini_base_url,
            settings.gemini_model,
            prompt,
            tools,
        )
        function_call_part = response.get("function_call_part")
        if function_call_part and tools:
            if "thoughtSignature" not in function_call_part:
                function_call_part["thoughtSignature"] = "skip_thought_signature_validator"
            try:
                async with Client(settings.mcp_server_url) as client:
                    tool_name = function_call_part.get("functionCall", {}).get("name")
                    args = function_call_part.get("functionCall", {}).get("args") or {}
                    if tool_name:
                        if tool_name.startswith("gcal."):
                            args["credential_id"] = credential_map.get("google_calendar")
                        if tool_name == "gcal.list_events":
                            args.setdefault("max_results", 10)
                            args.setdefault("order_by", "startTime")
                            args.setdefault("single_events", True)
                        if tool_name == "gcal.create_event":
                            args = {
                                "credential_id": args.get("credential_id"),
                                "jwt": args.get("jwt"),
                                "payload": {
                                    "calendar_id": args.get("calendar_id"),
                                    "event": args.get("event") or {},
                                },
                            }
                        if tool_name == "gcal.update_event":
                            args = {
                                "credential_id": args.get("credential_id"),
                                "calendar_id": args.get("calendar_id"),
                                "event_id": args.get("event_id"),
                                "payload": args.get("payload") or {},
                                "jwt": args.get("jwt"),
                            }
                        if "jwt" in args:
                            args["jwt"] = jwt
                        else:
                            args = {**args, "jwt": jwt}
                        if tool_name.startswith("gcal.") and not args.get("credential_id"):
                            raise ValueError("google_calendar credential not set for this room")
                    tool_result = await client.call_tool(tool_name, args)
                    safe_result = _make_jsonable(tool_result)
                follow = await gemini.generate_with_function_result(
                    api_key,
                    settings.gemini_base_url,
                    settings.gemini_model,
                    prompt,
                    function_call_part,
                    {"result": safe_result},
                    tools,
                )
                llm_text = follow.get("text")
                if not llm_text:
                    raw_json = json.dumps(safe_result, ensure_ascii=False)
                    summary = await gemini.generate(
                        api_key,
                        settings.gemini_base_url,
                        settings.gemini_model,
                        {"prompt": f"Summarize the following JSON result for the user in plain Japanese:\\n{raw_json}"},
                    )
                    summary_text = summary.get("text") or "(no summary)"
                    llm_text = f"{summary_text}\n\n---\nDebug JSON:\n{raw_json}"
            except Exception as exc:
                llm_text = f"Tool call failed: {exc}"
        else:
            llm_text = response.get("text") or str(response)

    assistant_content = llm_text if llm_text else tool_note or "(no response)"
    conn.execute(
        "INSERT INTO chat_messages (id, room_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), room_id, "assistant", assistant_content, int(time.time())),
    )
    conn.commit()
    return RedirectResponse(f"/chat/{room_id}", status_code=302)

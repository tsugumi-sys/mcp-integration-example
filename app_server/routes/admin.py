from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth.session import delete_session, get_session

router = APIRouter()
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


@router.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse("/credentials")


@router.get("/credentials")
async def credential_list(request: Request, session=Depends(require_session)):
    rows = request.app.state.db.execute(
        "SELECT id, provider, name, status, created_at FROM credentials ORDER BY created_at DESC"
    ).fetchall()
    return TEMPLATES.TemplateResponse(
        "credentials.html",
        {"request": request, "credentials": rows, "session": session},
    )


@router.post("/credentials")
async def credential_create(
    request: Request,
    provider: str = Form(""),
    name: str = Form(""),
    session=Depends(require_session),
):
    if not provider or not name:
        raise HTTPException(status_code=400, detail="provider and name required")
    credential_id = str(uuid.uuid4())
    now = int(time.time())
    request.app.state.db.execute(
        "INSERT INTO credentials (id, provider, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (credential_id, provider, name, "draft", now, now),
    )
    request.app.state.db.commit()
    return RedirectResponse(f"/credentials/{credential_id}", status_code=302)


@router.get("/credentials/{credential_id}")
async def credential_detail(request: Request, credential_id: str, session=Depends(require_session)):
    row = request.app.state.db.execute(
        "SELECT id, provider, name, status, created_at, updated_at FROM credentials WHERE id = ?",
        (credential_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="credential not found")
    token = request.app.state.db.execute(
        "SELECT access_token, refresh_token, expiry, scope, token_type FROM oauth_tokens WHERE credential_id = ?",
        (credential_id,),
    ).fetchone()
    gemini_key_tail = None
    if row["provider"] == "gemini" and token and token["access_token"]:
        gemini_key_tail = token["access_token"][-4:]
    return TEMPLATES.TemplateResponse(
        "credential_detail.html",
        {
            "request": request,
            "credential": row,
            "token": token,
            "session": session,
            "gemini_key_tail": gemini_key_tail,
        },
    )


@router.post("/credentials/{credential_id}/delete")
async def credential_delete(request: Request, credential_id: str, session=Depends(require_session)):
    request.app.state.db.execute("DELETE FROM oauth_tokens WHERE credential_id = ?", (credential_id,))
    request.app.state.db.execute("DELETE FROM credentials WHERE id = ?", (credential_id,))
    request.app.state.db.commit()
    return RedirectResponse("/credentials", status_code=302)


@router.post("/credentials/{credential_id}/gemini/save")
async def gemini_save(
    request: Request,
    credential_id: str,
    api_key: str = Form(""),
    session=Depends(require_session),
):
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key required")
    row = request.app.state.db.execute(
        "SELECT provider FROM credentials WHERE id = ?",
        (credential_id,),
    ).fetchone()
    if not row or row["provider"] != "gemini":
        raise HTTPException(status_code=400, detail="invalid credential")
    now = int(time.time())
    request.app.state.db.execute(
        "REPLACE INTO oauth_tokens (credential_id, access_token, refresh_token, expiry, scope, token_type, extra_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (credential_id, api_key, None, None, None, "api_key", None, now),
    )
    request.app.state.db.execute(
        "UPDATE credentials SET status = ?, updated_at = ? WHERE id = ?",
        ("connected", now, credential_id),
    )
    request.app.state.db.commit()
    return RedirectResponse(f"/credentials/{credential_id}", status_code=302)


@router.post("/auth/logout")
async def logout(request: Request):
    session_id = request.cookies.get(COOKIE_NAME)
    if session_id:
        delete_session(request.app.state.db, session_id)
    response = RedirectResponse("/auth/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response

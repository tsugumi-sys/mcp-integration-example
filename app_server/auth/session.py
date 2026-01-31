from __future__ import annotations

import time
import uuid
from typing import Optional

import sqlite3


def create_session(conn: sqlite3.Connection, email: str, ttl_seconds: int) -> str:
    session_id = str(uuid.uuid4())
    now = int(time.time())
    expires_at = now + ttl_seconds
    conn.execute(
        "INSERT INTO admin_sessions (id, email, expires_at, created_at) VALUES (?, ?, ?, ?)",
        (session_id, email, expires_at, now),
    )
    conn.commit()
    return session_id


def get_session(conn: sqlite3.Connection, session_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT id, email, expires_at FROM admin_sessions WHERE id = ?",
        (session_id,),
    ).fetchone()
    if not row:
        return None
    if row["expires_at"] < int(time.time()):
        delete_session(conn, session_id)
        return None
    return {"id": row["id"], "email": row["email"], "expires_at": row["expires_at"]}


def delete_session(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute("DELETE FROM admin_sessions WHERE id = ?", (session_id,))
    conn.commit()

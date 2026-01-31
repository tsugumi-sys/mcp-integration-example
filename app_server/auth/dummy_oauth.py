from __future__ import annotations

import time
import uuid
from typing import Optional

import sqlite3


def create_code(conn: sqlite3.Connection, email: str, state: str, ttl_seconds: int) -> str:
    code = str(uuid.uuid4())
    now = int(time.time())
    expires_at = now + ttl_seconds
    conn.execute(
        "INSERT INTO dummy_oauth_codes (code, email, state, expires_at, created_at) VALUES (?, ?, ?, ?, ?)",
        (code, email, state, expires_at, now),
    )
    conn.commit()
    return code


def consume_code(conn: sqlite3.Connection, code: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT code, email, state, expires_at FROM dummy_oauth_codes WHERE code = ?",
        (code,),
    ).fetchone()
    if not row:
        return None
    conn.execute("DELETE FROM dummy_oauth_codes WHERE code = ?", (code,))
    conn.commit()
    if row["expires_at"] < int(time.time()):
        return None
    return {"code": row["code"], "email": row["email"], "state": row["state"]}

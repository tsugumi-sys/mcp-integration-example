from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS credentials (
            id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            client_id TEXT,
            created_at INTEGER,
            updated_at INTEGER
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            credential_id TEXT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expiry INTEGER,
            scope TEXT,
            token_type TEXT,
            extra_json TEXT,
            updated_at INTEGER,
            FOREIGN KEY(credential_id) REFERENCES credentials(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_states (
            state TEXT PRIMARY KEY,
            credential_id TEXT,
            provider TEXT,
            expires_at INTEGER,
            FOREIGN KEY (credential_id) REFERENCES credentials(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_sessions (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            expires_at INTEGER,
            created_at INTEGER
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dummy_oauth_codes (
            code TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            state TEXT NOT NULL,
            expires_at INTEGER,
            created_at INTEGER
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_rooms (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            llm_provider TEXT NOT NULL,
            llm_credential_id TEXT,
            created_at INTEGER
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            room_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at INTEGER,
            FOREIGN KEY(room_id) REFERENCES chat_rooms(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_room_providers (
            room_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            credential_id TEXT,
            created_at INTEGER,
            PRIMARY KEY (room_id, provider),
            FOREIGN KEY(room_id) REFERENCES chat_rooms(id)
        )
        """
    )
    conn.commit()

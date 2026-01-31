from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_host: str
    app_port: int
    database_path: str
    jwt_secret: str
    jwt_issuer: str
    jwt_ttl_seconds: int
    admin_session_ttl_seconds: int
    dummy_oauth_client_id: str
    dummy_oauth_client_secret: str
    google_client_id: str
    google_client_secret: str
    gemini_api_key: str
    gemini_base_url: str
    gemini_model: str
    mcp_server_url: str


DEFAULT_DB_PATH = str(Path(__file__).resolve().parent / "data" / "app.db")


def load_settings() -> Settings:
    return Settings(
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        database_path=os.getenv("DATABASE_PATH", DEFAULT_DB_PATH),
        jwt_secret=os.getenv("JWT_SECRET", "change-me"),
        jwt_issuer=os.getenv("JWT_ISSUER", "app-server"),
        jwt_ttl_seconds=int(os.getenv("JWT_TTL_SECONDS", "900")),
        admin_session_ttl_seconds=int(os.getenv("ADMIN_SESSION_TTL_SECONDS", "3600")),
        dummy_oauth_client_id=os.getenv("DUMMY_OAUTH_CLIENT_ID", "dummy-client"),
        dummy_oauth_client_secret=os.getenv(
            "DUMMY_OAUTH_CLIENT_SECRET", "dummy-secret"
        ),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_base_url=os.getenv(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta",
        ),
        gemini_model=os.getenv("GEMINI_MODEL", "models/gemini-3-flash-preview"),
        mcp_server_url=os.getenv("MCP_SERVER_URL", "http://127.0.0.1:9001/mcp"),
    )

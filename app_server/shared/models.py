from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Provider(str, Enum):
    GOOGLE_CALENDAR = "google_calendar"
    GEMINI = "gemini"


class AuthTokenRequest(BaseModel):
    client_id: str
    client_secret: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class ApiError(BaseModel):
    error: str
    detail: Optional[str] = None


class ProviderResponse(BaseModel):
    provider: Provider
    data: Any = Field(default_factory=dict)


class GeminiRequest(BaseModel):
    prompt: str
    model: str = "gemini-3-flash-preview"


class GeminiResponse(BaseModel):
    text: str
    raw: Any = Field(default_factory=dict)

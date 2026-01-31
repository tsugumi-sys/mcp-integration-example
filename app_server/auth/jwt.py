from __future__ import annotations

import time
from typing import Any

import jwt


def issue_jwt(secret: str, issuer: str, ttl_seconds: int, subject: str) -> tuple[str, int]:
    now = int(time.time())
    exp = now + ttl_seconds
    payload = {
        "iss": issuer,
        "sub": subject,
        "iat": now,
        "exp": exp,
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token, exp


def verify_jwt(token: str, secret: str, issuer: str) -> dict[str, Any]:
    return jwt.decode(token, secret, algorithms=["HS256"], issuer=issuer)

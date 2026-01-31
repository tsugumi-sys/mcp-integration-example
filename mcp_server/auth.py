from __future__ import annotations


def require_jwt(jwt: str | None) -> str:
    if not jwt:
        raise ValueError("missing jwt")
    return jwt

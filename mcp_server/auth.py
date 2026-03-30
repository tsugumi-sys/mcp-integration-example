from __future__ import annotations

from fastmcp import Context


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def jwt_from_context(ctx: Context | None) -> str | None:
    if not ctx:
        return None
    request = getattr(ctx.request_context, "request", None)
    headers = getattr(request, "headers", None)
    if headers is None:
        return None
    if hasattr(headers, "get"):
        return _extract_bearer_token(headers.get("authorization"))
    return None


def require_jwt(jwt: str | None = None, ctx: Context | None = None) -> str:
    token = jwt or jwt_from_context(ctx)
    if not token:
        raise ValueError("missing jwt")
    return token

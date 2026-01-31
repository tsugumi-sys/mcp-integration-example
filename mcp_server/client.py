from __future__ import annotations

import httpx


def _headers(jwt: str) -> dict:
    return {"Authorization": f"Bearer {jwt}"}


async def get(app_server_url: str, path: str, jwt: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{app_server_url}{path}", headers=_headers(jwt), params=params)
    resp.raise_for_status()
    return resp.json()


async def post(app_server_url: str, path: str, jwt: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(f"{app_server_url}{path}", headers=_headers(jwt), json=payload)
    resp.raise_for_status()
    return resp.json()

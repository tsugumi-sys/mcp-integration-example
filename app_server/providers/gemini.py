from __future__ import annotations

import httpx


def _extract_text(payload: dict) -> str:
    try:
        return payload["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return ""


def _extract_function_call_part(payload: dict) -> dict | None:
    try:
        parts = payload["candidates"][0]["content"]["parts"]
    except Exception:
        return None
    for part in parts:
        if "functionCall" in part:
            return part
    return None


def _build_contents(prompt: str) -> list:
    return [{"role": "user", "parts": [{"text": prompt}]}]


def _normalize_model(model: str) -> str:
    if model.startswith("models/"):
        return model
    return f"models/{model}"


async def generate(api_key: str, base_url: str, model: str, payload: dict) -> dict:
    if not api_key:
        return {"error": "GEMINI_API_KEY not set"}
    prompt = payload.get("prompt", "")
    model = _normalize_model(payload.get("model", model))
    body = {"contents": _build_contents(prompt)}
    url = f"{base_url}/{model}:generateContent?key={api_key}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=body)
    if resp.status_code >= 400:
        return {"error": "gemini request failed", "detail": resp.text}
    data = resp.json()
    return {"text": _extract_text(data), "raw": data}


async def generate_with_tools(api_key: str, base_url: str, model: str, prompt: str, tools: list[dict]) -> dict:
    if not api_key:
        return {"error": "GEMINI_API_KEY not set"}
    model = _normalize_model(model)
    body = {
        "contents": _build_contents(prompt),
        "tools": tools,
    }
    url = f"{base_url}/{model}:generateContent?key={api_key}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=body)
    if resp.status_code >= 400:
        return {"error": "gemini request failed", "detail": resp.text}
    data = resp.json()
    return {"text": _extract_text(data), "function_call_part": _extract_function_call_part(data), "raw": data}


async def generate_with_function_result(
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    function_call_part: dict,
    function_result: dict,
    tools: list[dict],
) -> dict:
    if not api_key:
        return {"error": "GEMINI_API_KEY not set"}
    model = _normalize_model(model)
    contents = _build_contents(prompt)
    contents.append({"role": "model", "parts": [function_call_part]})
    function_call = function_call_part.get("functionCall", {})
    contents.append(
        {
            "role": "user",
            "parts": [
                {
                    "functionResponse": {
                        "name": function_call.get("name"),
                        "response": function_result,
                    }
                }
            ],
        }
    )
    body = {
        "contents": contents,
        "tools": tools,
    }
    url = f"{base_url}/{model}:generateContent?key={api_key}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=body)
    if resp.status_code >= 400:
        return {"error": "gemini request failed", "detail": resp.text}
    data = resp.json()
    return {"text": _extract_text(data), "raw": data}

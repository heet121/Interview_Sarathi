"""One-off Gemini connectivity check — prints status only, never the API key."""
import asyncio
import json
import sys

import httpx

from config import settings


async def main() -> int:
    key = (settings.GEMINI_API_KEY or "").strip()
    if not key or key.lower().startswith("your-"):
        print("FAIL: GEMINI_API_KEY missing or still placeholder in .env")
        return 1

    url = f"{settings.GEMINI_BASE_URL}/models/{settings.GEMINI_MODEL}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}
    body = {
        "contents": [{"role": "user", "parts": [{"text": "Reply with exactly: OK"}]}],
        "generationConfig": {"maxOutputTokens": 10},
    }

    print(f"Model: {settings.GEMINI_MODEL}")
    print(f"Key format: {'AQ auth key' if key.startswith('AQ.') else 'AIza standard key' if key.startswith('AIza') else 'unknown prefix'}")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=body)
    except Exception as exc:
        print(f"FAIL: network error — {exc}")
        return 1

    print(f"HTTP status: {resp.status_code}")

    if resp.status_code == 200:
        try:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            print(f"OK: Gemini responded — {text.strip()[:80]!r}")
        except (KeyError, IndexError, TypeError):
            print("OK: Gemini returned 200 (unexpected response shape)")
        return 0

    try:
        err = resp.json().get("error", {})
        msg = err.get("message") or resp.text[:300]
        reason = err.get("status", "")
    except json.JSONDecodeError:
        msg = resp.text[:300]
        reason = ""

    print(f"FAIL: {reason or 'error'} — {msg}")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

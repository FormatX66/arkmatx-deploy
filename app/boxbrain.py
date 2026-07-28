from urllib.parse import urlsplit

import httpx


async def boxbrain_status(settings) -> dict:
    if not settings.boxbrain_url:
        return {"configured": False, "status": "not-connected", "mode": "safe"}

    parsed = urlsplit(settings.boxbrain_url)
    if parsed.scheme not in {"https", "http"}:
        return {"configured": True, "status": "blocked", "reason": "unsupported URL"}
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost"}:
        return {"configured": True, "status": "blocked", "reason": "HTTPS required"}

    headers = {}
    if settings.boxbrain_token:
        headers["Authorization"] = f"Bearer {settings.boxbrain_token}"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(settings.boxbrain_url.rstrip("/") + "/health", headers=headers)
            response.raise_for_status()
        return {"configured": True, "status": "online", "code": response.status_code}
    except Exception as exc:  # status reporting must not crash the control room
        return {"configured": True, "status": "offline", "reason": type(exc).__name__}

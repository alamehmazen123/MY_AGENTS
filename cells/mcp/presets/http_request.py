"""Make an HTTP request (GET/POST/etc.) to any URL — generic REST/API client."""

SCHEMA = {
    "name": "http_request",
    "description": "Call any HTTP(S) API. params: method, url, headers, params, json, data.",
    "parameters": {
        "method": {"type": "string"}, "url": {"type": "string"},
        "headers": {"type": "object"}, "params": {"type": "object"},
        "json": {"type": "object"}, "data": {"type": "string"},
    },
    "required": ["url"],
}


def handle(args: dict) -> dict:
    url = (args.get("url") or "").strip()
    if not url:
        return {"error": "missing_url"}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    method = (args.get("method") or "GET").upper()
    try:
        import httpx
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.request(
                method, url,
                headers=args.get("headers") or None,
                params=args.get("params") or None,
                json=args.get("json") if args.get("json") is not None else None,
                data=args.get("data") if args.get("data") is not None else None,
            )
        body = resp.text
        out = {"status": resp.status_code, "url": str(resp.url),
               "content_type": resp.headers.get("content-type", ""),
               "body": body[:8000], "truncated": len(body) > 8000}
        try:
            out["json"] = resp.json()
        except Exception:
            pass
        return out
    except Exception as e:
        return {"error": str(e), "url": url}

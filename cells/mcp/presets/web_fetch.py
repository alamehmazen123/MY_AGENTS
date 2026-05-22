"""cells/mcp/presets/web_fetch.py — Fetch a web page and return its title and visible text.

This is a best-effort HTTP fetcher (not a JS-rendering browser): it returns the
page title and the visible text content, which the agent can read/summarize.
"""
import re

SCHEMA = {
    "name": "web_fetch",
    "description": "Fetch a URL over HTTP(S) and return its title and visible text.",
    "parameters": {
        "url": {"type": "string"},
        "max_chars": {"type": "integer"},
    },
    "required": ["url"],
}

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def _strip_html(html: str) -> str:
    # Drop scripts/styles, then all tags, then collapse whitespace.
    text = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z#0-9]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def handle(args: dict) -> dict:
    url = (args.get("url") or "").strip()
    if not url:
        return {"error": "missing_url"}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    max_chars = int(args.get("max_chars", 2000) or 2000)
    try:
        import httpx
        with httpx.Client(timeout=20, follow_redirects=True,
                          headers={"User-Agent": _UA, "Accept": "text/html"}) as client:
            resp = client.get(url)
            status = resp.status_code
            raw = resp.text[:800_000]
    except Exception as e:
        return {"error": str(e), "url": url}

    title_m = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.I | re.S)
    title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else ""
    # Pull candidate headline tags so news pages surface something useful.
    heads = re.findall(r"<h[12][^>]*>(.*?)</h[12]>", raw, flags=re.I | re.S)
    headlines = [re.sub(r"<[^>]+>", " ", h) for h in heads]
    headlines = [re.sub(r"\s+", " ", h).strip() for h in headlines]
    headlines = [h for h in headlines if h][:15]
    text = _strip_html(raw)
    return {
        "url": url,
        "status": status,
        "title": title,
        "headlines": headlines,
        "text": text[:max_chars],
        "text_length": len(text),
    }

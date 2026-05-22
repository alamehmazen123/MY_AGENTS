"""Search Wikipedia and fetch an article summary (no API key)."""
import json
import urllib.parse
import urllib.request

SCHEMA = {
    "name": "wikipedia",
    "description": "Search Wikipedia and return matching titles plus the top article summary.",
    "parameters": {"query": {"type": "string"}},
    "required": ["query"],
}

# Wikipedia/Cloudflare blocks some HTTP client fingerprints (httpx) with 403;
# the stdlib urllib client is accepted, so we use it here.
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def handle(args: dict) -> dict:
    query = (args.get("query") or args.get("title") or "").strip()
    if not query:
        return {"error": "missing_query"}
    try:
        search_url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "list": "search", "srsearch": query, "srlimit": 5, "format": "json",
        })
        titles = []
        try:
            data = _get_json(search_url)
            titles = [h["title"] for h in data.get("query", {}).get("search", [])]
        except Exception:
            titles = []

        target = titles[0] if titles else query
        summary = None
        try:
            t = urllib.parse.quote(target.replace(" ", "_"))
            j = _get_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{t}")
            summary = {
                "title": j.get("title"),
                "extract": j.get("extract"),
                "url": (j.get("content_urls", {}) or {}).get("desktop", {}).get("page"),
            }
        except Exception:
            summary = None

        return {"query": query, "results": titles, "summary": summary}
    except Exception as e:
        return {"error": str(e), "query": query}

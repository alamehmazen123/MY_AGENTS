"""cells/mcp/presets/web_fetch.py — Fetch a web page and return its title and visible text.

This is a best-effort HTTP fetcher (not a JS-rendering browser): it returns the
page title, candidate headlines, and the visible text, which the agent reads.
"""
import re

SCHEMA = {
    "name": "web_fetch",
    "description": "Fetch a URL over HTTP(S) and return its title, headlines, and visible text.",
    "parameters": {
        "url": {"type": "string"},
        "max_chars": {"type": "integer"},
    },
    "required": ["url"],
}

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# Nav/footer link texts that are not real headlines.
_NAV_JUNK = (
    "terms", "privacy", "cookie", "sign in", "log in", "subscribe", "advertise",
    "accessibility", "contact us", "about us", "careers", "newsletter", "follow",
    "download", "settings", "feedback", "site map", "do not sell", "ad choices",
)


def _is_nav_junk(text: str) -> bool:
    low = text.lower()
    if any(j in low for j in _NAV_JUNK):
        return True
    # Real headlines are sentences; require at least a couple of words.
    return len(text.split()) < 3


def _strip_html(html: str) -> str:
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

    is_rss = "<rss" in raw[:500].lower() or "<feed" in raw[:500].lower() or url.endswith((".rss", ".xml"))
    if is_rss:
        # RSS/Atom feed: every <item>/<entry> <title> is a real headline.
        items = re.findall(r"<item[^>]*>(.*?)</item>", raw, flags=re.I | re.S)
        items += re.findall(r"<entry[^>]*>(.*?)</entry>", raw, flags=re.I | re.S)
        headlines = []
        for it in items:
            tm = re.search(r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, flags=re.I | re.S)
            if tm:
                h = re.sub(r"<[^>]+>", " ", tm.group(1))
                h = re.sub(r"\s+", " ", h).strip()
                if h:
                    headlines.append(h)
        headlines = headlines[:15]
    else:
        heads = re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", raw, flags=re.I | re.S)
        headlines = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip() for h in heads]
        headlines = [h for h in headlines if h and not _is_nav_junk(h)]
        # Fallback for text-only/"lite" news pages: link texts are the headlines.
        if len(headlines) < 3:
            for a in re.findall(r"<a[^>]*>(.*?)</a>", raw, flags=re.I | re.S):
                h = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", a)).strip()
                if 20 <= len(h) <= 200 and h not in headlines and not _is_nav_junk(h):
                    headlines.append(h)
        headlines = headlines[:15]

    text = _strip_html(raw)
    return {
        "url": url,
        "status": status,
        "title": title,
        "headlines": headlines,
        "text": text[:max_chars],
        "text_length": len(text),
    }

"""Convert a web page (by URL) or an HTML string into clean plain text."""
import re

SCHEMA = {
    "name": "html_to_markdown",
    "description": "Strip a web page or HTML string down to clean readable text.",
    "parameters": {"url": {"type": "string"}, "html": {"type": "string"}, "max_chars": {"type": "integer"}},
    "required": [],
}


def handle(args: dict) -> dict:
    html = args.get("html", "")
    url = (args.get("url") or "").strip()
    max_chars = int(args.get("max_chars", 6000) or 6000)
    try:
        if url and not html:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            import httpx
            with httpx.Client(timeout=20, follow_redirects=True,
                              headers={"User-Agent": "Mozilla/5.0"}) as client:
                html = client.get(url).text
        if not html:
            return {"error": "missing_html_or_url"}
        text = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
        text = re.sub(r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", r"\2 (\1)", text, flags=re.I | re.S)
        text = re.sub(r"<h([1-6])[^>]*>(.*?)</h\1>", r"\n\n\2\n", text, flags=re.I | re.S)
        text = re.sub(r"<(p|br|li|div)[^>]*>", "\n", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&[a-zA-Z#0-9]+;", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()
        return {"text": text[:max_chars], "length": len(text), "url": url or None}
    except Exception as e:
        return {"error": str(e), "url": url}

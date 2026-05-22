"""Search arXiv research papers (no API key)."""
import re

SCHEMA = {
    "name": "arxiv",
    "description": "Search arXiv and return paper titles, authors, abstracts and links.",
    "parameters": {"query": {"type": "string"}, "max_results": {"type": "integer"}},
    "required": ["query"],
}


def _grab(block: str, tag: str) -> str:
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", block, flags=re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def handle(args: dict) -> dict:
    query = (args.get("query") or "").strip()
    if not query:
        return {"error": "missing_query"}
    max_results = int(args.get("max_results", 5) or 5)
    try:
        import httpx
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            r = client.get("https://export.arxiv.org/api/query", params={
                "search_query": f"all:{query}", "start": 0, "max_results": max_results,
            })
            xml = r.text
        papers = []
        for entry in re.findall(r"<entry>(.*?)</entry>", xml, flags=re.S):
            authors = re.findall(r"<name>(.*?)</name>", entry, flags=re.S)
            papers.append({
                "title": _grab(entry, "title"),
                "authors": [re.sub(r"\s+", " ", a).strip() for a in authors][:6],
                "summary": _grab(entry, "summary")[:600],
                "published": _grab(entry, "published"),
                "link": _grab(entry, "id"),
            })
        return {"query": query, "count": len(papers), "papers": papers}
    except Exception as e:
        return {"error": str(e), "query": query}

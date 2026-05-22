"""Extract text from a PDF file (pypdf)."""

SCHEMA = {
    "name": "pdf_extract",
    "description": "Extract text from a local PDF file.",
    "parameters": {"path": {"type": "string"}, "max_pages": {"type": "integer"}},
    "required": ["path"],
}


def handle(args: dict) -> dict:
    path = args.get("path", "")
    if not path:
        return {"error": "missing_path"}
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        total = len(reader.pages)
        max_pages = int(args.get("max_pages", total) or total)
        parts = []
        for page in reader.pages[:max_pages]:
            parts.append(page.extract_text() or "")
        text = "\n".join(parts)
        return {"path": path, "page_count": total, "pages_read": min(max_pages, total),
                "text": text[:8000], "truncated": len(text) > 8000}
    except Exception as e:
        return {"error": str(e), "path": path}

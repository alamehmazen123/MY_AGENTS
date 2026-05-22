"""Word/line/character/sentence counts and reading time for a text (no network)."""
import re

SCHEMA = {
    "name": "text_stats",
    "description": "Count words, lines, characters, sentences and estimate reading time of a text.",
    "parameters": {"text": {"type": "string"}},
    "required": ["text"],
}


def handle(args: dict) -> dict:
    text = args.get("text", "")
    if not text:
        return {"error": "missing_text"}
    words = re.findall(r"\b\w+\b", text)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    return {
        "characters": len(text),
        "characters_no_spaces": len(re.sub(r"\s", "", text)),
        "words": len(words),
        "lines": text.count("\n") + 1,
        "sentences": len(sentences),
        "reading_time_min": round(len(words) / 200, 2),
    }

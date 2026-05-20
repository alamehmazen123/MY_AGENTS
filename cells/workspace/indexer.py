"""
cells/workspace/indexer.py — Incremental Symbol + Keyword Index
"""
from pathlib import Path
from typing import Dict, List, Set
import re


class IncrementalIndexer:
    """Incremental file indexer."""
    
    def __init__(self):
        self._index: Dict[str, Set[str]] = {}  # word -> file paths
    
    def index_file(self, path: Path):
        text = path.read_text(encoding="utf-8", errors="ignore")
        words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))
        for w in words:
            self._index.setdefault(w.lower(), set()).add(str(path))
    
    def search(self, keyword: str) -> List[str]:
        return sorted(self._index.get(keyword.lower(), set()))

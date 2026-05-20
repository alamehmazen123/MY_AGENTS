"""
cells/gateway/upload.py — Chunked File Streaming
"""
from pathlib import Path
from typing import Dict
import hashlib
from kernel.config import settings


class UploadHandler:
    """Chunked upload with content-addressed storage."""
    
    def __init__(self):
        self.store_dir = settings.data_dir / "vacuoles"
        self.store_dir.mkdir(parents=True, exist_ok=True)
    
    def store(self, data: bytes) -> Dict:
        h = hashlib.sha256(data).hexdigest()
        path = self.store_dir / h[:2] / h[2:4] / h
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"hash": h, "size": len(data), "path": str(path)}
    
    def retrieve(self, h: str) -> bytes:
        path = self.store_dir / h[:2] / h[2:4] / h
        if path.exists():
            return path.read_bytes()
        return b""

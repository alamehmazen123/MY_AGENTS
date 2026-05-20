"""
plasma/blob_store.py — Content-Addressed, Deduplicated
"""
from pathlib import Path
import hashlib
from kernel.config import settings


class BlobStore:
    """Content-addressed blob storage."""
    
    def __init__(self):
        self.dir = settings.data_dir / "vacuoles"
        self.dir.mkdir(parents=True, exist_ok=True)
    
    def put(self, data: bytes) -> str:
        h = hashlib.sha256(data).hexdigest()
        path = self.dir / h[:2] / h[2:4] / h
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return h
    
    def get(self, h: str) -> bytes:
        path = self.dir / h[:2] / h[2:4] / h
        return path.read_bytes() if path.exists() else b""
    
    def exists(self, h: str) -> bool:
        return (self.dir / h[:2] / h[2:4] / h).exists()


blobs = BlobStore()

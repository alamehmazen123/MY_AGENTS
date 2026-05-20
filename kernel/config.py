"""
kernel/config.py — Pydantic Settings, Env Cascade
"""
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List


class Config(BaseSettings):
    # Runtime
    env: str = Field(default="development", alias="MY_AGENTS_ENV")
    log_level: str = Field(default="INFO", alias="MY_AGENTS_LOG_LEVEL")
    
    # Paths
    data_dir: Path = Field(default=Path("data"), alias="MY_AGENTS_DATA_DIR")
    workspace_root: Path = Field(default=Path("."), alias="MY_AGENTS_WORKSPACE_ROOT")
    
    # Ollama
    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")
    ollama_default_model: str = Field(default="qwen2.5-coder:14b", alias="OLLAMA_DEFAULT_MODEL")
    ollama_max_context: int = Field(default=32768, alias="OLLAMA_MAX_CONTEXT")
    
    # Runtime invariants
    max_tokens_per_deliberation: int = Field(default=12000, alias="MY_AGENTS_MAX_TOKENS")
    max_iterations: int = Field(default=4, alias="MY_AGENTS_MAX_ITERATIONS")
    max_runtime_seconds: int = Field(default=45, alias="MY_AGENTS_MAX_RUNTIME")
    queue_depth_limit: int = Field(default=100, alias="MY_AGENTS_QUEUE_DEPTH")
    
    # Thermal
    thermal_threshold_c: float = Field(default=85.0, alias="MY_AGENTS_THERMAL_THRESHOLD")
    
    # Recovery
    recovery_time_ms: int = Field(default=5000, alias="MY_AGENTS_RECOVERY_TIME_MS")
    snapshot_interval_seconds: int = Field(default=30, alias="MY_AGENTS_SNAPSHOT_INTERVAL")
    
    # Gateway
    api_port: int = Field(default=8000, alias="MY_AGENTS_API_PORT")
    ws_port: int = Field(default=8001, alias="MY_AGENTS_WS_PORT")
    cors_origins: List[str] = Field(default=["http://localhost:5173"], alias="MY_AGENTS_CORS_ORIGINS")
    
    @field_validator("data_dir", "workspace_root", mode="before")
    @classmethod
    def _resolve_path(cls, v):
        return Path(v).expanduser().resolve()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton
settings = Config()

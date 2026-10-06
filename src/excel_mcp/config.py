"""Configuration models for the Excel execution environment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExecutorConfig:
    input_dir: Path
    output_dir: Path
    input_volume: str | None = None
    output_volume: str | None = None
    image: str = "excel-mcp-executor:latest"
    timeout_seconds: int = 30
    memory: str = "512m"
    cpus: str = "1.0"
    pids_limit: str = "64"
    max_output_bytes: int = 1_000_000

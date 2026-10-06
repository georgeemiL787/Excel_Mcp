"""Backward-compatible import shim for the executor module."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from excel_mcp.executor import DockerExecutor
from excel_mcp.config import ExecutorConfig

__all__ = ["DockerExecutor", "ExecutorConfig"]

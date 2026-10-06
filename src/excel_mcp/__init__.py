"""Excel MCP assistant package."""

from .config import ExecutorConfig
from .executor import DockerExecutor

__all__ = ["DockerExecutor", "ExecutorConfig"]

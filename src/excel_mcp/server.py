"""stdio MCP server exposing one isolated Excel execution tool."""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

from mcp.server.fastmcp import FastMCP

from .config import ExecutorConfig
from .executor import DockerExecutor


def _path_from_env(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default)).expanduser().resolve()


def build_config() -> ExecutorConfig:
    control_plane_container = Path("/.dockerenv").exists() and Path("/var/run/docker.sock").exists()
    default_input_volume = "excel-assistant-inputs" if control_plane_container else ""
    default_output_volume = "excel-assistant-outputs" if control_plane_container else ""
    return ExecutorConfig(
        input_dir=_path_from_env("EXCEL_INPUT_DIR", "inputs"),
        output_dir=_path_from_env("EXCEL_OUTPUT_DIR", "outputs"),
        input_volume=os.environ.get("EXCEL_INPUT_VOLUME", default_input_volume) or None,
        output_volume=os.environ.get("EXCEL_OUTPUT_VOLUME", default_output_volume) or None,
        image=os.environ.get("EXCEL_EXECUTION_IMAGE", "excel-mcp-executor:latest"),
        timeout_seconds=int(os.environ.get("EXCEL_EXECUTION_TIMEOUT_SECONDS", "30")),
    )


config = build_config()
executor = DockerExecutor(config)
call_lock = Lock()
mcp = FastMCP("excel-assistant")


@mcp.tool()
def execute_python(code: str) -> dict:
    """Execute Python for Excel work inside an isolated Docker container.

    Available libraries: openpyxl, pandas, numpy, matplotlib. Read files from
    /inputs and write new or edited files to /outputs. Assign a JSON value to
    `result` for it to be returned. openpyxl writes formulas but does not
    calculate them.
    """
    with call_lock:
        return executor.execute(code)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

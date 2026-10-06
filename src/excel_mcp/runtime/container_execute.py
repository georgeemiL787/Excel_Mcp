"""Execution shim copied into the restricted Docker image."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import time
import traceback
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd

MAX_OUTPUT_BYTES = 1_000_000


def json_value(value: Any) -> Any:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"result is not JSON-serializable: {exc}") from exc
    return value


def main() -> None:
    payload = json.load(sys.stdin)
    code = payload["code"]
    stdout = io.StringIO()
    stderr = io.StringIO()
    started = time.perf_counter()
    response: dict[str, Any] = {
        "success": False, "stdout": "", "stderr": "", "result": None,
        "artifacts": [], "execution_time_ms": 0, "error": None,
    }
    namespace = {
        "openpyxl": openpyxl, "pd": pd, "pandas": pd, "np": np,
        "numpy": np, "plt": plt,
    }
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exec(compile(code, "<execute_python>", "exec"), namespace, namespace)
        response["success"] = True
        response["result"] = json_value(namespace.get("result")) if "result" in namespace else None
    except Exception as exc:
        response["error"] = {"type": type(exc).__name__, "message": str(exc)}
        traceback.print_exc(file=stderr)
    finally:
        response["stdout"] = stdout.getvalue()[:MAX_OUTPUT_BYTES]
        response["stderr"] = stderr.getvalue()[:MAX_OUTPUT_BYTES]
        response["execution_time_ms"] = round((time.perf_counter() - started) * 1000, 2)
        plt.close("all")
    print(json.dumps(response, default=str, separators=(",", ":")))


if __name__ == "__main__":
    main()

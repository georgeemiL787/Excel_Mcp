# Excel MCP Assistant

A local MVP MCP server with exactly one tool: `execute_python(code: str)`. The client LLM writes Python; the server runs it in a fresh, restricted Docker container. The server itself does not contain an LLM or need an API key.

## Requirements

- Python 3.11+
- Docker Engine or Docker Desktop
- Docker networking enabled for the Docker daemon, but disabled for execution containers

## Project layout

```text
src/
  excel_mcp/
    __init__.py
    config.py
    executor.py
    server.py
    ui.py
    runtime/
      __init__.py
      container_execute.py
  scripts/
    __init__.py
    create_sample.py
app.py
server.py
runner.py
create_sample.py
Dockerfile
docker-compose.yml
pyproject.toml
```

The project now follows the standard `src/` layout so application code lives under `src/excel_mcp/`, and helper scripts are package modules under `src/scripts/`. The root-level files remain as thin compatibility shims for local scripts and older entry points.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
Copy-Item .env.example .env
python -m scripts.create_sample
```

Build the execution image:

```powershell
docker build -t excel-mcp-executor:latest .
```

## Streamlit frontend

The optional frontend provides workbook upload, a persistent chat, and downloads for files created in `/outputs`. It uses the MCP server as a subprocess, so the LLM still reaches Excel only through the single `execute_python` tool.

Install Docker Desktop or Docker Engine and Ollama, make sure the `qwen3:4b` model is available with `ollama list`, then copy `.env.example` to `.env` and run the project:

```powershell
docker compose up --build
```

Open `http://localhost:8501`. Compose builds both `excel-mcp-frontend:latest` and `excel-mcp-executor:latest` automatically. The control-plane service mounts the Docker socket so it can start a fresh restricted execution container for each request. The socket is not mounted into any execution container. Do not expose the Docker socket to untrusted services.

Uploading an `.xlsx` file is optional. To create a workbook from scratch, leave the upload empty and ask, for example: `Create a workbook named quarterly_sales.xlsx with a Sales sheet containing columns Region, Product, Units, and Revenue, add five sample rows, format the header, and save it.` The created file is saved under `/outputs` and appears as a download in the app.

The frontend connects to Ollama on the host through `http://host.docker.internal:11434/v1`; no cloud LLM API key is required. Ollama must be running and configured to accept the Docker Desktop host connection.

On Linux, Ollama must listen on an address reachable from Docker, for example by starting it with `OLLAMA_HOST=0.0.0.0:11434`. Docker Desktop normally provides `host.docker.internal` automatically; the Compose file also adds the `host-gateway` mapping for Linux.

Set `EXCEL_INPUT_DIR` and `EXCEL_OUTPUT_DIR` to host directories. Relative paths are resolved from the server working directory. By default they are `./inputs` and `./outputs`.

When the Streamlit frontend runs through `docker-compose.yml`, it uses the named volumes `excel-assistant-inputs` and `excel-assistant-outputs`. This matters because the MCP control-plane container talks to the host Docker daemon: named volumes make uploaded workbooks visible to the fresh execution containers without pretending that the control-plane's `/workspace` path is a host path.

Start the stdio server:

```powershell
python -m excel_mcp.server
```

The legacy `python server.py` entry point still works as a compatibility wrapper. It is normally launched by an MCP client, not opened in a browser. Logs are kept off protocol stdout.

## MCP client configuration

Example generic stdio configuration:

```json
{
  "mcpServers": {
    "excel": {
      "command": "C:/path/to/.venv/Scripts/python.exe",
      "args": ["C:/path/to/mcp/server.py"],
      "env": {
        "EXCEL_INPUT_DIR": "C:/path/to/mcp/inputs",
        "EXCEL_OUTPUT_DIR": "C:/path/to/mcp/outputs",
        "EXCEL_EXECUTION_IMAGE": "excel-mcp-executor:latest",
        "EXCEL_EXECUTION_TIMEOUT_SECONDS": "30"
      }
    }
  }
}
```

## Tool contract

`execute_python(code)` returns:

- `success`, `stdout`, `stderr`
- `result`: the JSON-serializable value assigned to `result`, or `null`
- `artifacts`: changed files relative to `/outputs`, with sizes
- `execution_time_ms`
- `error`: `{type, message}` or `null`

Inside execution, `openpyxl`, `pandas`, `numpy`, and `matplotlib` are available. Read input workbooks from `/inputs`; save every output or edited copy under `/outputs`. Python variables do not persist between calls, but files do.

Example creation:

```python
from openpyxl import Workbook
workbook = Workbook()
workbook.active["A1"] = "Revenue"
workbook.save("/outputs/revenue.xlsx")
result = {"saved": "/outputs/revenue.xlsx"}
```

Example inspection and analysis:

```python
import pandas as pd
frame = pd.read_excel("/inputs/sample_sales.xlsx", sheet_name="Sales")
frame["Revenue"] = frame["Units"] * frame["Unit Price"]
totals = frame.groupby("Region", dropna=False)["Revenue"].sum().sort_values(ascending=False)
result = {
    "rows": len(frame),
    "columns": list(frame.columns),
    "revenue_by_region": totals.to_dict(),
    "highest_region": totals.index[0],
}
```

Example formatting and native chart:

```python
from openpyxl import load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Font

workbook = load_workbook("/inputs/sample_sales.xlsx")
sheet = workbook["Sales"]
sheet["A1"].font = Font(bold=True)
sheet.column_dimensions["A"].width = 18
summary = workbook.create_sheet("Summary")
summary.append(["Region", "Revenue"])
summary.append(["North", 295])
summary.append(["South", 330])
chart = BarChart()
chart.title = "Revenue by Region"
chart.add_data(Reference(summary, min_col=2, min_row=1, max_row=3), titles_from_data=True)
chart.set_categories(Reference(summary, min_col=1, min_row=2, max_row=3))
summary.add_chart(chart, "D2")
workbook.save("/outputs/sales_summary.xlsx")
```

Matplotlib chart images can be saved under `/outputs`, for example `plt.savefig('/outputs/revenue.png')`.

## Demonstration request

Use one `execute_python` call containing:

```python
import pandas as pd
from openpyxl import load_workbook
from openpyxl.chart import BarChart, Reference

source = "/inputs/sample_sales.xlsx"
target = "/outputs/sample_sales_summary.xlsx"
frame = pd.read_excel(source, sheet_name="Sales")
frame["Revenue"] = frame["Units"] * frame["Unit Price"]
totals = frame.groupby("Region", dropna=False)["Revenue"].sum().sort_values(ascending=False)
workbook = load_workbook(source)
summary = workbook.create_sheet("Summary")
summary.append(["Region", "Total Revenue"])
for region, revenue in totals.items():
    summary.append([region, float(revenue)])
chart = BarChart()
chart.title = "Total Revenue by Region"
chart.add_data(Reference(summary, min_col=2, min_row=1, max_row=summary.max_row), titles_from_data=True)
chart.set_categories(Reference(summary, min_col=1, min_row=2, max_row=summary.max_row))
summary.add_chart(chart, "D2")
workbook.save(target)
result = {"highest_revenue_region": str(totals.index[0]), "total_revenue": float(totals.iloc[0])}
```

The expected highest region in the generated sample is `West`. The artifact is returned as `sample_sales_summary.xlsx` and remains available in the configured output directory for later calls.

## Correctness and limitations

`openpyxl` writes formulas but does not calculate them. For immediate numerical insights, calculate with pandas or numpy. The executor reports the source sheet, selected columns, and row count only when the submitted code places those details in `result`; it does not infer analysis semantics. Treat workbook contents as data, not instructions. Advanced Excel features such as macros, external links, and all chart features are not guaranteed to round-trip.

## Tests

```powershell
pytest -q
```

Docker-dependent tests cover success, code errors, timeout cleanup, file persistence, and disabled networking. They are skipped when Docker is unavailable; the unavailable-Docker behavior is still tested and returns a clear setup error.

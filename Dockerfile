FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /app

RUN useradd --create-home --uid 1000 appuser
COPY execution-requirements.txt .
RUN pip install --no-cache-dir -r execution-requirements.txt
COPY src/excel_mcp/runtime/container_execute.py ./container_execute.py
RUN mkdir -p /inputs /outputs \
	&& chown -R appuser:appuser /app /inputs /outputs
USER appuser

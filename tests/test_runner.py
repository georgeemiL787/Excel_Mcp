import json
import shutil
import subprocess
from pathlib import Path

import pytest

from excel_mcp.executor import DockerExecutor
from excel_mcp.config import ExecutorConfig


ROOT = Path(__file__).parents[1]
DOCKER_AVAILABLE = (
    shutil.which("docker") is not None
    and subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0
)
IMAGE_AVAILABLE = (
    DOCKER_AVAILABLE
    and subprocess.run(
        ["docker", "image", "inspect", "excel-mcp-executor:latest"],
        capture_output=True,
        check=False,
    ).returncode == 0
)


def executor(tmp_path):
    return DockerExecutor(ExecutorConfig(tmp_path / "inputs", tmp_path / "outputs"))


def test_missing_docker_returns_setup_error(tmp_path):
    result = executor(tmp_path).execute("result = 1")
    if DOCKER_AVAILABLE:
        pytest.skip("Docker is available; this test targets the unavailable setup path")
    assert result["success"] is False
    assert result["error"]["type"] == "DockerUnavailable"


@pytest.mark.skipif(not IMAGE_AVAILABLE, reason="Docker and the execution image are required")
def test_success_and_result(tmp_path):
    result = executor(tmp_path).execute("print('hello'); result = {'value': 3}")
    assert result["success"] is True
    assert result["stdout"] == "hello\n"
    assert result["result"] == {"value": 3}


@pytest.mark.skipif(not IMAGE_AVAILABLE, reason="Docker and the execution image are required")
def test_code_error(tmp_path):
    result = executor(tmp_path).execute("raise ValueError('bad input')")
    assert result["success"] is False
    assert result["error"]["type"] == "ValueError"


@pytest.mark.skipif(not IMAGE_AVAILABLE, reason="Docker and the execution image are required")
def test_file_persists_between_calls(tmp_path):
    first = executor(tmp_path).execute("open('/outputs/state.txt', 'w').write('ok')")
    second = executor(tmp_path).execute("result = open('/outputs/state.txt').read()")
    assert first["success"] and second["result"] == "ok"


@pytest.mark.skipif(not IMAGE_AVAILABLE, reason="Docker and the execution image are required")
def test_timeout_cleanup(tmp_path):
    configured = DockerExecutor(ExecutorConfig(tmp_path / "inputs", tmp_path / "outputs", timeout_seconds=1))
    result = configured.execute("import time; time.sleep(10)")
    assert result["success"] is False
    assert result["error"]["type"] == "TimeoutError"


@pytest.mark.skipif(not IMAGE_AVAILABLE, reason="Docker and the execution image are required")
def test_network_is_disabled(tmp_path):
    result = executor(tmp_path).execute("import urllib.request; urllib.request.urlopen('https://example.com')")
    assert result["success"] is False

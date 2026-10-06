"""Docker-backed execution for the Excel MCP server."""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from .config import ExecutorConfig


class DockerExecutor:
    def __init__(self, config: ExecutorConfig) -> None:
        self.config = config
        self.config.input_dir.mkdir(parents=True, exist_ok=True)
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, code: str) -> dict[str, Any]:
        started = time.perf_counter()
        before = self._snapshot_outputs()
        payload = json.dumps({"code": code})
        container_name = f"excel-mcp-{uuid.uuid4().hex}"
        command = self._docker_command(container_name)
        try:
            completed = subprocess.run(
                command,
                input=payload,
                text=True,
                capture_output=True,
                timeout=self.config.timeout_seconds + 5,
                check=False,
            )
        except FileNotFoundError:
            return self._error("DockerUnavailable", "Docker executable was not found", started)
        except subprocess.TimeoutExpired:
            self._remove_container(container_name)
            return self._error("TimeoutError", "Execution container did not terminate", started)
        finally:
            self._remove_container(container_name)

        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout).strip()
            error_type = "ContainerError"
            if completed.returncode == 124:
                error_type = "TimeoutError"
            return self._error(error_type, message or f"container exited with {completed.returncode}", started)

        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return self._error("ProtocolError", "Execution container returned invalid JSON", started)

        response["artifacts"] = self._new_artifacts(before)
        response["execution_time_ms"] = round((time.perf_counter() - started) * 1000, 2)
        return response

    def _docker_command(self, container_name: str) -> list[str]:
        input_mount = (
            f"type=volume,source={self.config.input_volume},destination=/inputs,readonly"
            if self.config.input_volume
            else self._input_bind_or_empty_mount()
        )
        output_mount = (
            f"type=volume,source={self.config.output_volume},destination=/outputs"
            if self.config.output_volume
            else f"type=bind,src={self.config.output_dir},dst=/outputs"
        )
        return [
            "docker", "run", "--rm", "-i", "--network", "none",
            "--name", container_name,
            "--user", "1000:1000", "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--cpus", self.config.cpus, "--memory", self.config.memory,
            "--pids-limit", self.config.pids_limit, "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--mount", input_mount,
            "--mount", output_mount,
            self.config.image, "python", "/app/container_execute.py",
        ]

    def _input_bind_or_empty_mount(self) -> str:
        if any(path.is_file() for path in self.config.input_dir.rglob("*")):
            return f"type=bind,src={self.config.input_dir},dst=/inputs,readonly"
        return "type=tmpfs,destination=/inputs,tmpfs-mode=0555"

    def _remove_container(self, container_name: str) -> None:
        try:
            subprocess.run(
                ["docker", "rm", "--force", container_name],
                capture_output=True,
                check=False,
            )
        except FileNotFoundError:
            pass

    def _snapshot_outputs(self) -> dict[str, tuple[int, int]]:
        snapshot: dict[str, tuple[int, int]] = {}
        for path in self.config.output_dir.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(self.config.output_dir).as_posix()
            stat = path.stat()
            snapshot[relative] = (stat.st_mtime_ns, stat.st_size)
        return snapshot

    def _new_artifacts(self, before: dict[str, tuple[int, int]]) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        for relative, metadata in self._snapshot_outputs().items():
            if before.get(relative) != metadata:
                artifacts.append({"path": relative, "size": metadata[1]})
        return sorted(artifacts, key=lambda item: item["path"])

    def _error(self, error_type: str, message: str, started: float) -> dict[str, Any]:
        return {
            "success": False,
            "stdout": "",
            "stderr": message[: self.config.max_output_bytes],
            "result": None,
            "artifacts": [],
            "execution_time_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": {"type": error_type, "message": message[: self.config.max_output_bytes]},
        }

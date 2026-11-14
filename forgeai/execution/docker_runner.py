"""Run approved project tests in a restricted Docker container.

This runner is opt-in and intended for a dedicated local/disposable VM. It never
executes project source in the Streamlit process. The Docker daemon remains a
privileged host service, so container isolation is not a substitute for a
dedicated execution host.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import ValidationError

from forgeai.agents.contracts import CodeGenerationDocument


DEFAULT_IMAGE = "forgeai-test-runner:py311"
MAX_TIMEOUT_SECONDS = 120
MAX_OUTPUT_BYTES = 16_000


@dataclass(frozen=True)
class TestExecutionReport:
    status: str
    exit_code: int | None
    duration_seconds: float
    test_files: list[str]
    output: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def docker_runner_enabled() -> bool:
    """Execution is disabled unless an operator explicitly opts in."""
    return os.getenv("FORGEAI_ENABLE_DOCKER_RUNNER", "false").strip().lower() == "true"


def _test_paths(bundle: CodeGenerationDocument) -> list[str]:
    paths = []
    for item in bundle.files:
        path = PurePosixPath(item.path)
        if path.suffix == ".py" and (
            path.name.startswith("test_") or path.name.endswith("_test.py")
        ):
            paths.append(item.path)
    return sorted(paths)


def _write_bundle(bundle: CodeGenerationDocument, destination: Path) -> None:
    root = destination.resolve()
    for item in bundle.files:
        target = destination.joinpath(*PurePosixPath(item.path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        resolved_parent = target.parent.resolve()
        if root not in (resolved_parent, *resolved_parent.parents):
            raise ValueError("A generated file path escaped the temporary workspace.")
        target.write_text(item.content, encoding="utf-8")
    # The container runs as UID 65534; make the read-only bind mount traversable.
    for entry in sorted(destination.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        entry.chmod(0o755 if entry.is_dir() else 0o644)
    destination.chmod(0o755)


def _read_output(process: subprocess.Popen, limit: int, state: dict[str, Any]) -> None:
    """Drain Docker output without allowing unbounded host-side buffering."""
    stream = process.stdout
    if stream is None:
        return
    while True:
        chunk = stream.read(4096)
        if not chunk:
            break
        remaining = limit - len(state["output"])
        if remaining > 0:
            state["output"].extend(chunk[:remaining])
        if len(chunk) > remaining:
            state["truncated"] = True
            try:
                process.kill()
            except OSError:
                pass
            break


class DockerTestRunner:
    """Execute test_*.py files from a human-approved bundle in Docker."""

    def __init__(
        self,
        image: str | None = None,
        docker_binary: str = "docker",
        max_output_bytes: int = MAX_OUTPUT_BYTES,
    ) -> None:
        self.image = image or os.getenv("FORGEAI_DOCKER_IMAGE", DEFAULT_IMAGE)
        self.docker_binary = docker_binary
        self.max_output_bytes = max(1024, min(max_output_bytes, MAX_OUTPUT_BYTES))

    def run(
        self,
        source_bundle: dict[str, Any],
        *,
        approved: bool,
        enabled: bool | None = None,
        timeout_seconds: int = 60,
    ) -> TestExecutionReport:
        started = time.monotonic()
        if enabled is None:
            enabled = docker_runner_enabled()
        if enabled is not True:
            return TestExecutionReport("disabled", None, 0.0, [], "",
                                       "Docker execution is disabled. Set FORGEAI_ENABLE_DOCKER_RUNNER=true on a trusted local runner.")
        if approved is not True:
            return TestExecutionReport("blocked", None, 0.0, [], "",
                                       "Execution requires explicit human approval of this source bundle.")

        try:
            bundle = CodeGenerationDocument.model_validate(source_bundle)
        except (ValidationError, TypeError, ValueError) as exc:
            return TestExecutionReport("invalid_bundle", None, 0.0, [], "",
                                       f"Source bundle validation failed: {str(exc)[:500]}")

        test_files = _test_paths(bundle)
        if not test_files:
            return TestExecutionReport("no_tests", None, 0.0, [], "",
                                       "No Python test files named test_*.py or *_test.py were found in the approved source bundle.")

        timeout = max(1, min(int(timeout_seconds), MAX_TIMEOUT_SECONDS))
        container_name = "forgeai-test-" + uuid.uuid4().hex[:16]
        command = [
            self.docker_binary, "run", "--rm", "--pull=never",
            "--name", container_name,
            "--network=none", "--read-only",
            "--cap-drop=ALL", "--security-opt=no-new-privileges",
            "--pids-limit=64", "--memory=256m", "--memory-swap=256m",
            "--cpus=1.0", "--shm-size=16m", "--ulimit", "nofile=256:256",
            "--user=65534:65534",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m",
            "--env", "HOME=/tmp",
            "--env", "PYTHONPATH=/workspace",
            "--env", "PYTHONDONTWRITEBYTECODE=1",
            "--env", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
            "--mount", "type=bind,source={source},target=/workspace,readonly",
            "--workdir", "/workspace",
            self.image,
            "python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
            "--disable-warnings", *[f"/workspace/{path}" for path in test_files],
        ]

        with tempfile.TemporaryDirectory(prefix="forgeai-test-") as temp_dir:
            try:
                _write_bundle(bundle, Path(temp_dir))
                command[command.index("--mount") + 1] = (
                    f"type=bind,source={temp_dir},target=/workspace,readonly"
                )
                process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    bufsize=0,
                )
            except FileNotFoundError:
                return TestExecutionReport(
                    "runner_unavailable", None, round(time.monotonic() - started, 3),
                    test_files, "", "Docker CLI was not found. Install Docker Desktop/Engine and enable the runner only on a trusted local machine."
                )
            except OSError as exc:
                return TestExecutionReport(
                    "runner_unavailable", None, round(time.monotonic() - started, 3),
                    test_files, "", f"Docker could not be started: {str(exc)[:300]}"
                )

            output_state: dict[str, Any] = {"output": bytearray(), "truncated": False}
            reader = threading.Thread(
                target=_read_output,
                args=(process, self.max_output_bytes, output_state),
                daemon=True,
            )
            reader.start()
            timed_out = False
            try:
                exit_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                exit_code = process.wait()
            reader.join(timeout=3)

            # A killed Docker client can leave its container behind. Always try to
            # remove this uniquely named job; cleanup failure is reported, not hidden.
            try:
                cleanup = subprocess.run(
                    [self.docker_binary, "rm", "-f", container_name],
                    capture_output=True, text=True, timeout=8, check=False,
                )
                cleanup_warning = cleanup.returncode != 0 and "No such container" not in (cleanup.stderr or "")
            except (OSError, subprocess.TimeoutExpired):
                cleanup_warning = True
            output = bytes(output_state["output"]).decode("utf-8", errors="replace")
            if output_state["truncated"]:
                output += "\n[Output truncated at the configured limit; container stopped.]"
            if timed_out:
                status = "timed_out"
                message = f"Test execution exceeded the {timeout}-second time limit."
            elif output_state["truncated"]:
                status = "output_limit_exceeded"
                message = "Test output exceeded the configured limit; the container was stopped."
            elif exit_code == 0:
                status = "passed"
                message = "The approved test suite completed successfully inside the restricted Docker container."
            else:
                status = "failed"
                message = f"The test process exited with code {exit_code}."
            if cleanup_warning:
                message += " Docker cleanup returned a warning; inspect the runner host."
            return TestExecutionReport(
                status, exit_code, round(time.monotonic() - started, 3),
                test_files, output[:self.max_output_bytes + 120], message,
            )

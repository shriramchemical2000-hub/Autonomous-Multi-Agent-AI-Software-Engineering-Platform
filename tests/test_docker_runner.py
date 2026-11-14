import io
import os
import subprocess

import pytest

from forgeai.execution.docker_runner import DockerTestRunner, docker_runner_enabled


BUNDLE = {
    "implementation_summary": "Tiny example",
    "implementation_notes": [],
    "files": [
        {"path": "src/math_ops.py", "language": "python", "purpose": "Math operations",
         "content": "def add(a, b):\n    return a + b\n"},
        {"path": "tests/test_math_ops.py", "language": "python", "purpose": "Unit tests",
         "content": "from src.math_ops import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"},
    ],
}


class FakeProcess:
    def __init__(self, return_code=0, output=b"1 passed in 0.01s"):
        self.stdout = io.BytesIO(output)
        self.return_code = return_code
        self.killed = False

    def wait(self, timeout=None):
        return self.return_code

    def kill(self):
        self.killed = True


def test_runner_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("FORGEAI_ENABLE_DOCKER_RUNNER", raising=False)
    assert docker_runner_enabled() is False
    result = DockerTestRunner().run(BUNDLE, approved=True)
    assert result.status == "disabled"


def test_runner_requires_explicit_bundle_approval():
    result = DockerTestRunner().run(BUNDLE, approved=False, enabled=True)
    assert result.status == "blocked"


def test_runner_does_not_start_when_bundle_has_no_tests(monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("Docker must not start"))
    bundle = {**BUNDLE, "files": [BUNDLE["files"][0]]}
    result = DockerTestRunner().run(bundle, approved=True, enabled=True)
    assert result.status == "no_tests"


def test_runner_command_enforces_container_restrictions(monkeypatch, tmp_path):
    process = FakeProcess()
    calls = []

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))
        return process

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = DockerTestRunner().run(BUNDLE, approved=True, enabled=True)

    assert result.status == "passed"
    assert result.exit_code == 0
    assert result.test_files == ["tests/test_math_ops.py"]
    command = calls[0][0]
    for flag in ("--network=none", "--read-only", "--cap-drop=ALL",
                 "--security-opt=no-new-privileges", "--pids-limit=64",
                 "--memory=256m", "--memory-swap=256m", "--cpus=1.0",
                 "--user=65534:65534"):
        assert flag in command
    assert "--env" in command and "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1" in command
    mount = command[command.index("--mount") + 1]
    assert mount.endswith(",target=/workspace,readonly")
    assert "python" in command and "-m" in command and "pytest" in command
    assert calls[-1][0][1:3] == ["rm", "-f"]


def test_runner_reports_missing_docker(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("docker missing")
    monkeypatch.setattr(subprocess, "Popen", missing)
    result = DockerTestRunner().run(BUNDLE, approved=True, enabled=True)
    assert result.status == "runner_unavailable"


def test_runner_caps_timeout(monkeypatch):
    process = FakeProcess()
    calls = []
    monkeypatch.setattr(subprocess, "Popen", lambda command, **kwargs: (calls.append(command) or process))
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", ""))
    result = DockerTestRunner().run(BUNDLE, approved=True, enabled=True, timeout_seconds=9999)
    assert result.status == "passed"

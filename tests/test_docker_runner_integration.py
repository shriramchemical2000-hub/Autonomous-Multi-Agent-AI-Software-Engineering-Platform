import os

import pytest

from forgeai.execution.docker_runner import DockerTestRunner


@pytest.mark.skipif(
    os.getenv("FORGEAI_DOCKER_INTEGRATION") != "true",
    reason="Docker integration test runs only in the CI Docker job.",
)
def test_approved_bundle_runs_inside_docker():
    bundle = {
        "implementation_summary": "Docker runner smoke test",
        "implementation_notes": [],
        "files": [{
            "path": "tests/test_smoke.py",
            "language": "python",
            "purpose": "Known safe CI smoke test",
            "content": "def test_runner_smoke():\n    assert 6 * 7 == 42\n",
        }],
    }
    report = DockerTestRunner().run(
        bundle, approved=True, enabled=True, timeout_seconds=30
    )
    assert report.status == "passed", report.output or report.message
    assert "1 passed" in report.output

import json

import pytest

from forgeai.agents.code_repairer import AgentExecutionError, CodeRepairer
from forgeai.agents.contracts import AgentContext


BUNDLE = {
    "implementation_summary": "Initial implementation",
    "implementation_notes": [],
    "files": [
        {"path": "src/math_ops.py", "language": "python", "purpose": "Math helpers",
         "content": "def add(a, b):\n    return a - b\n"},
        {"path": "tests/test_math_ops.py", "language": "python", "purpose": "Tests",
         "content": "from src.math_ops import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"},
    ],
}
REQUIREMENTS = {"product_name": "Math", "functional_requirements": []}


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        return self.responses.pop(0)


def test_repairer_returns_candidate_and_preserves_tests():
    response = {
        "repair_summary": "Fix addition implementation.",
        "changes": [{
            "file_path": "src/math_ops.py",
            "replacement_content": "def add(a, b):\n    return a + b\n",
            "rationale": "The implementation used subtraction.",
            "addresses": ["test_add failure"],
        }],
        "addressed_findings": ["test_add failure"],
        "unresolved_risks": [],
    }
    provider = FakeProvider([json.dumps(response)])
    result = CodeRepairer(provider).run(AgentContext(
        project_id=1, user_request="Repair the failed test.",
        prior_artifacts={
            "requirements": REQUIREMENTS, "code_bundle": BUNDLE,
            "execution_report": {"status": "failed", "output": "assert 2 == 5"},
            "repair_attempt": 1,
        },
    ))
    candidate = result.artifact["code_bundle"]
    assert "return a + b" in candidate["files"][0]["content"]
    assert candidate["files"][1]["content"] == BUNDLE["files"][1]["content"]
    assert result.status == "needs_review"


def test_repairer_cannot_modify_test_files():
    response = {
        "repair_summary": "Tamper with tests.",
        "changes": [{
            "file_path": "tests/test_math_ops.py",
            "replacement_content": "def test_fake(): pass",
            "rationale": "Make it pass.",
            "addresses": [],
        }],
        "addressed_findings": [],
        "unresolved_risks": [],
    }
    provider = FakeProvider([json.dumps(response), json.dumps(response)])
    with pytest.raises(AgentExecutionError, match="failed validation"):
        CodeRepairer(provider).run(AgentContext(
            project_id=1, user_request="Repair.",
            prior_artifacts={
                "requirements": REQUIREMENTS, "code_bundle": BUNDLE,
                "execution_report": {"status": "failed", "output": "failure"},
            },
        ))


def test_repairer_requires_failure_evidence():
    provider = FakeProvider([])
    with pytest.raises(AgentExecutionError, match="failed test execution"):
        CodeRepairer(provider).run(AgentContext(
            project_id=1, user_request="Repair.",
            prior_artifacts={"requirements": REQUIREMENTS, "code_bundle": BUNDLE},
        ))
    assert provider.calls == 0


def test_repairer_rejects_paths_outside_source_bundle():
    response = {
        "repair_summary": "Change unknown file.",
        "changes": [{
            "file_path": "src/not_present.py",
            "replacement_content": "print('x')",
            "rationale": "Unknown.",
            "addresses": [],
        }],
        "addressed_findings": [],
        "unresolved_risks": [],
    }
    provider = FakeProvider([json.dumps(response), json.dumps(response)])
    with pytest.raises(AgentExecutionError, match="failed validation"):
        CodeRepairer(provider).run(AgentContext(
            project_id=1, user_request="Repair.",
            prior_artifacts={
                "requirements": REQUIREMENTS, "code_bundle": BUNDLE,
                "execution_report": {"status": "failed", "output": "failure"},
            },
        ))

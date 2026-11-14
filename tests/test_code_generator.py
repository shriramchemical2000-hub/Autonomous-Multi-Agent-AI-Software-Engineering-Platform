import json

import pytest
from pydantic import ValidationError

from forgeai.agents.contracts import AgentContext, CodeGenerationDocument
from forgeai.agents.code_generator import AgentExecutionError, CodeGenerator


VALID_BUNDLE = {
    "implementation_summary": "A small booking API vertical slice.",
    "implementation_notes": ["Review before running locally."],
    "files": [{
        "path": "src/app.py",
        "language": "python",
        "purpose": "Application entry point.",
        "content": "def health():\n    return {'status': 'ok'}\n",
    }, {
        "path": "README.md",
        "language": "markdown",
        "purpose": "Local setup instructions.",
        "content": "# Example\n\nReview this source before running it.\n",
    }],
}


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, *, system_prompt, user_prompt, temperature=0.2):
        self.calls.append(user_prompt)
        return self.responses.pop(0)


def make_context():
    return AgentContext(
        project_id=12,
        user_request="Implement the approved product.",
        prior_artifacts={
            "requirements": {"product_name": "Example"},
            "architecture": {"system_overview": "A modular app."},
            "uiux_design": {"design_overview": "A clear interface."},
        },
    )


def test_code_generator_returns_bounded_unexecuted_source_bundle():
    provider = FakeProvider([json.dumps(VALID_BUNDLE)])
    result = CodeGenerator(provider).run(make_context())
    assert result.status == "needs_review"
    assert len(result.artifact["code_bundle"]["files"]) == 2
    assert "not been executed" in result.summary
    assert "approved UI/UX" in provider.calls[0].lower() or "APPROVED UI/UX DESIGN" in provider.calls[0]


def test_code_generator_requires_all_three_upstream_artifacts():
    provider = FakeProvider([json.dumps(VALID_BUNDLE)])
    context = AgentContext(
        project_id=12, user_request="Implement it.",
        prior_artifacts={"requirements": {}, "architecture": {}},
    )
    with pytest.raises(AgentExecutionError, match="requirements, architecture, and UI/UX"):
        CodeGenerator(provider).run(context)
    assert provider.calls == []


def test_code_generator_retries_invalid_json_once():
    provider = FakeProvider(["not-json", json.dumps(VALID_BUNDLE)])
    result = CodeGenerator(provider).run(make_context())
    assert result.status == "needs_review"
    assert len(provider.calls) == 2


def test_code_generator_stops_after_two_invalid_responses():
    provider = FakeProvider(["bad", "still bad"])
    with pytest.raises(AgentExecutionError, match="after 2 attempts"):
        CodeGenerator(provider).run(make_context())
    assert len(provider.calls) == 2


@pytest.mark.parametrize("unsafe_path", [
    "../outside.py", "/tmp/outside.py", "C:/outside.py", "src\\escape.py",
    ".github/workflows/build.yml", "src/.env", "src/data.bin",
])
def test_generated_file_rejects_unsafe_paths(unsafe_path):
    payload = {**VALID_BUNDLE, "files": [{**VALID_BUNDLE["files"][0], "path": unsafe_path}]}
    with pytest.raises(ValidationError):
        CodeGenerationDocument.model_validate(payload)


def test_generated_file_rejects_duplicate_paths():
    payload = {**VALID_BUNDLE, "files": [VALID_BUNDLE["files"][0], VALID_BUNDLE["files"][0]]}
    with pytest.raises(ValidationError, match="duplicate file paths"):
        CodeGenerationDocument.model_validate(payload)



def test_generated_bundle_rejects_per_file_and_total_size_limits():
    oversized_file = {**VALID_BUNDLE, "files": [{**VALID_BUNDLE["files"][0], "content": "x" * 30001}]}
    with pytest.raises(ValidationError):
        CodeGenerationDocument.model_validate(oversized_file)

    many_files = [
        {"path": f"src/file_{index}.py", "language": "python", "purpose": "test", "content": "x" * 10000}
        for index in range(21)
    ]
    oversized_bundle = {**VALID_BUNDLE, "files": many_files}
    with pytest.raises(ValidationError, match="200 KB"):
        CodeGenerationDocument.model_validate(oversized_bundle)


@pytest.mark.parametrize("reserved_path", [
    "src/CON.py", "src/name.py:stream", "src/trailing.py ", "src/trailing..py ",
])
def test_generated_file_rejects_windows_reserved_or_invalid_segments(reserved_path):
    payload = {**VALID_BUNDLE, "files": [{**VALID_BUNDLE["files"][0], "path": reserved_path}]}
    with pytest.raises(ValidationError):
        CodeGenerationDocument.model_validate(payload)

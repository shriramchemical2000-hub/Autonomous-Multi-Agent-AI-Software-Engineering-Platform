import json

import pytest

from forgeai.agents.contracts import AgentContext
from forgeai.agents.requirements_analyst import AgentExecutionError, RequirementsAnalyst


VALID_DOCUMENT = {
    "product_name": "Clinic Booking",
    "problem_statement": "Patients need a reliable way to book appointments.",
    "target_users": ["Patients", "Receptionists"],
    "scope_in": ["Appointment search", "Appointment booking"],
    "scope_out": ["Online payments"],
    "assumptions": ["Clinics maintain their own availability."],
    "functional_requirements": [
        {
            "requirement_id": "FR-001",
            "title": "Search appointments",
            "description": "A patient can view available appointment slots.",
            "priority": "must",
            "acceptance_criteria": ["Only open slots are displayed."],
        }
    ],
    "user_stories": [
        {
            "story_id": "US-001",
            "persona": "Patient",
            "action": "view available appointment slots",
            "benefit": "I can choose a suitable time.",
            "acceptance_criteria": ["The list shows date and time."],
            "related_requirement_ids": ["FR-001"],
        }
    ],
    "non_functional_requirements": ["Patient data must be protected from unauthorised access."],
    "open_questions": ["Which authentication provider should be used?"],
}


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, *, system_prompt, user_prompt, temperature=0.2):
        self.calls.append(
            {"system_prompt": system_prompt, "user_prompt": user_prompt, "temperature": temperature}
        )
        return self.responses.pop(0)


def make_context():
    return AgentContext(
        project_id=11,
        user_request="Build a clinic appointment booking platform.",
        constraints=["Use a responsive web interface", "Keep the first release payment-free"],
    )


def test_requirements_analyst_returns_validated_artifact():
    provider = FakeProvider([json.dumps(VALID_DOCUMENT)])
    result = RequirementsAnalyst(provider).run(make_context())

    assert result.status == "needs_review"
    assert result.agent_name == "Requirements Analyst"
    assert result.artifact["requirements"]["functional_requirements"][0]["requirement_id"] == "FR-001"
    assert result.artifact["requirements"]["user_stories"][0]["related_requirement_ids"] == ["FR-001"]
    assert len(provider.calls) == 1
    assert provider.calls[0]["temperature"] == 0.1
    assert result.warnings


def test_requirements_analyst_accepts_json_markdown_fence():
    provider = FakeProvider(["```json\n" + json.dumps(VALID_DOCUMENT) + "\n```"])
    result = RequirementsAnalyst(provider).run(make_context())
    assert result.artifact["requirements"]["product_name"] == "Clinic Booking"


def test_requirements_analyst_retries_once_after_invalid_json():
    provider = FakeProvider(["not json", json.dumps(VALID_DOCUMENT)])
    result = RequirementsAnalyst(provider).run(make_context())

    assert result.status == "needs_review"
    assert len(provider.calls) == 2
    assert "previous response" in provider.calls[1]["user_prompt"]


def test_requirements_analyst_stops_after_two_invalid_responses():
    provider = FakeProvider(["{}", "still not json"])
    with pytest.raises(AgentExecutionError, match="after 2 attempts"):
        RequirementsAnalyst(provider).run(make_context())
    assert len(provider.calls) == 2


def test_requirements_analyst_rejects_unexpected_schema_fields():
    invalid = dict(VALID_DOCUMENT, fabricated_extra_field="not allowed")
    provider = FakeProvider([json.dumps(invalid), json.dumps(invalid)])
    with pytest.raises(AgentExecutionError, match="valid specification"):
        RequirementsAnalyst(provider).run(make_context())
    assert len(provider.calls) == 2

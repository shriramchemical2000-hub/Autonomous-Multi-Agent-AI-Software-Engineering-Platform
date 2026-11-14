import json

import pytest

from forgeai.orchestration.workflow import build_forge_workflow


VALID_REQUIREMENTS = {
    "product_name": "Clinic Booking",
    "problem_statement": "Patients need to book appointments.",
    "target_users": ["Patients"],
    "scope_in": ["Appointment booking"],
    "scope_out": [],
    "assumptions": [],
    "functional_requirements": [],
    "user_stories": [],
    "non_functional_requirements": [],
    "open_questions": [],
}
VALID_ARCHITECTURE = {
    "system_overview": "A modular booking platform.",
    "components": [],
    "data_entities": ["Appointment"],
    "api_endpoints": [],
    "security_considerations": ["Protect patient data."],
    "design_decisions": ["Use a modular monolith initially."],
    "unresolved_risks": [],
}


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, *, system_prompt, user_prompt, temperature=0.2):
        self.calls.append(user_prompt)
        return self.responses.pop(0)


def test_requirements_stage_runs_and_stops_for_human_approval():
    provider = FakeProvider([json.dumps(VALID_REQUIREMENTS)])
    graph = build_forge_workflow(provider)

    result = graph.invoke({
        "project_id": 5,
        "user_request": "Build a clinic booking platform.",
        "requested_stage": "requirements",
    })

    assert result["requirements"]["product_name"] == "Clinic Booking"
    assert result["current_stage"] == "requirements_review"
    assert result["status"] == "awaiting_human_approval"
    assert len(provider.calls) == 1


def test_architecture_stage_is_blocked_without_explicit_approval():
    provider = FakeProvider([json.dumps(VALID_ARCHITECTURE)])
    graph = build_forge_workflow(provider)

    with pytest.raises(ValueError, match="explicitly approved"):
        graph.invoke({
            "project_id": 5,
            "user_request": "Design it.",
            "requested_stage": "architecture",
            "requirements": VALID_REQUIREMENTS,
            "requirements_approved": False,
        })

    assert provider.calls == []


def test_architecture_stage_consumes_approved_requirements_from_shared_state():
    provider = FakeProvider([json.dumps(VALID_ARCHITECTURE)])
    graph = build_forge_workflow(provider)

    result = graph.invoke({
        "project_id": 5,
        "user_request": "Build a clinic booking platform.",
        "requested_stage": "architecture",
        "requirements": VALID_REQUIREMENTS,
        "requirements_approved": True,
    })

    assert result["architecture"]["system_overview"] == "A modular booking platform."
    assert result["current_stage"] == "architecture_review"
    assert result["status"] == "awaiting_human_approval"
    assert "Clinic Booking" in provider.calls[0]


def test_unknown_stage_is_rejected_before_any_agent_runs():
    provider = FakeProvider([])
    graph = build_forge_workflow(provider)

    with pytest.raises(ValueError, match="requested_stage"):
        graph.invoke({"requested_stage": "deployment"})

    assert provider.calls == []

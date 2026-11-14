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
VALID_UIUX = {
    "design_overview": "A responsive booking experience.",
    "design_goals": ["Make booking clear."],
    "personas": ["Patient"],
    "user_journeys": [{
        "persona": "Patient", "goal": "Book", "entry_point": "Home",
        "steps": [{"step": 1, "user_action": "Select date", "system_response": "Show slots", "decision_or_exception": None}],
        "success_outcome": "Confirmation shown.",
    }],
    "navigation_structure": ["Home", "Bookings"],
    "screen_specifications": [{
        "screen_name": "Search", "purpose": "Find slots", "primary_user": "Patient",
        "layout_regions": ["Header", "Results"], "key_components": ["Slot card"],
        "primary_action": "Choose slot", "states_and_feedback": ["Loading", "Empty"],
        "validation_and_errors": ["Date is required"],
    }],
    "reusable_components": [{
        "component_name": "Slot card", "purpose": "Show slot", "behaviour": "Select slot",
        "accessibility_notes": ["Keyboard accessible"],
    }],
    "design_system": {
        "colour_tokens": ["primary blue"], "typography_scale": ["body 16px"],
        "spacing_and_layout_rules": ["8px base"], "visual_principles": ["Readable"],
    },
    "responsive_behaviour": ["Stack columns on mobile"],
    "accessibility_requirements": ["Label every field"],
    "usability_risks": [],
    "open_design_questions": [],
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
    result = build_forge_workflow(provider).invoke({
        "project_id": 5, "user_request": "Build a clinic booking platform.",
        "requested_stage": "requirements",
    })
    assert result["requirements"]["product_name"] == "Clinic Booking"
    assert result["status"] == "awaiting_human_approval"


def test_architecture_stage_requires_approved_requirements():
    provider = FakeProvider([json.dumps(VALID_ARCHITECTURE)])
    with pytest.raises(ValueError, match="explicitly approved"):
        build_forge_workflow(provider).invoke({
            "project_id": 5, "user_request": "Design it.", "requested_stage": "architecture",
            "requirements": VALID_REQUIREMENTS, "requirements_approved": False,
        })
    assert provider.calls == []


def test_architecture_stage_runs_with_approved_requirements():
    provider = FakeProvider([json.dumps(VALID_ARCHITECTURE)])
    result = build_forge_workflow(provider).invoke({
        "project_id": 5, "user_request": "Build it.", "requested_stage": "architecture",
        "requirements": VALID_REQUIREMENTS, "requirements_approved": True,
    })
    assert result["architecture"]["system_overview"] == "A modular booking platform."


def test_uiux_stage_requires_both_approval_gates():
    provider = FakeProvider([json.dumps(VALID_UIUX)])
    with pytest.raises(ValueError, match="architecture must be explicitly approved"):
        build_forge_workflow(provider).invoke({
            "project_id": 5, "user_request": "Design UX.", "requested_stage": "uiux",
            "requirements": VALID_REQUIREMENTS, "requirements_approved": True,
            "architecture": VALID_ARCHITECTURE, "architecture_approved": False,
        })
    assert provider.calls == []


def test_uiux_stage_consumes_both_approved_artifacts():
    provider = FakeProvider([json.dumps(VALID_UIUX)])
    result = build_forge_workflow(provider).invoke({
        "project_id": 5, "user_request": "Design UX.", "requested_stage": "uiux",
        "requirements": VALID_REQUIREMENTS, "requirements_approved": True,
        "architecture": VALID_ARCHITECTURE, "architecture_approved": True,
    })
    assert result["uiux_design"]["screen_specifications"][0]["screen_name"] == "Search"
    assert result["current_stage"] == "uiux_review"
    assert result["status"] == "awaiting_human_approval"
    assert "Clinic Booking" in provider.calls[0]


def test_unknown_stage_is_rejected():
    provider = FakeProvider([])
    with pytest.raises(ValueError, match="requested_stage"):
        build_forge_workflow(provider).invoke({"requested_stage": "deployment"})
    assert provider.calls == []

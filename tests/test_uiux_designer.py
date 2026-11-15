import json

import pytest

from forgeai.agents.contracts import AgentContext
from forgeai.agents.uiux_designer import AgentExecutionError, UIUXDesigner


VALID_DESIGN = {
    "design_overview": "A clear, responsive appointment booking experience.",
    "design_goals": ["Make available slots easy to compare."],
    "personas": ["Patient"],
    "user_journeys": [{
        "persona": "Patient",
        "goal": "Book an appointment",
        "entry_point": "Appointment search",
        "steps": [{"step": 1, "user_action": "Choose a date", "system_response": "Show available slots", "decision_or_exception": None}],
        "success_outcome": "A booking confirmation is shown.",
    }],
    "navigation_structure": ["Home", "Find appointment", "My bookings"],
    "screen_specifications": [{
        "screen_name": "Appointment Search",
        "purpose": "Find an available appointment.",
        "primary_user": "Patient",
        "layout_regions": ["Header", "Filters", "Results"],
        "key_components": ["Date picker", "Slot cards"],
        "primary_action": "Select a slot",
        "states_and_feedback": ["Loading", "No results", "Results loaded"],
        "validation_and_errors": ["Require a valid date."],
    }],
    "reusable_components": [{
        "component_name": "Slot card",
        "purpose": "Present a bookable time.",
        "behaviour": "Selects one available slot.",
        "accessibility_notes": ["Keyboard operable with visible focus."],
    }],
    "design_system": {
        "colour_tokens": ["primary: accessible blue"],
        "typography_scale": ["body: 16px"],
        "spacing_and_layout_rules": ["Use an 8px spacing base."],
        "visual_principles": ["Prioritise legibility."],
    },
    "responsive_behaviour": ["Collapse filters into a drawer on narrow screens."],
    "accessibility_requirements": ["All controls have programmatic labels."],
    "usability_risks": ["Users may confuse unavailable and fully booked slots."],
    "open_design_questions": ["Should patients be able to reschedule?"],
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
        project_id=9,
        user_request="Design clinic booking UX.",
        prior_artifacts={
            "requirements": {"product_name": "Clinic Booking", "functional_requirements": []},
            "architecture": {"system_overview": "Modular booking platform.", "components": []},
        },
    )


def test_uiux_designer_returns_complete_validated_artifact():
    provider = FakeProvider([json.dumps(VALID_DESIGN)])
    result = UIUXDesigner(provider).run(make_context())
    assert result.status == "needs_review"
    assert result.agent_name == "UI/UX Designer"
    assert result.artifact["uiux_design"]["screen_specifications"][0]["screen_name"] == "Appointment Search"
    assert "Clinic Booking" in provider.calls[0]
    assert result.warnings


def test_uiux_designer_accepts_markdown_json_fence():
    provider = FakeProvider(["```json\n" + json.dumps(VALID_DESIGN) + "\n```"])
    result = UIUXDesigner(provider).run(make_context())
    assert result.artifact["uiux_design"]["design_overview"]


def test_uiux_designer_repairs_minor_malformed_json_before_validation():
    malformed = json.dumps(VALID_DESIGN).replace('"design_overview":', 'design_overview:', 1)
    provider = FakeProvider([malformed])
    result = UIUXDesigner(provider).run(make_context())
    assert result.artifact["uiux_design"]["design_overview"] == VALID_DESIGN["design_overview"]


def test_uiux_designer_requires_both_prior_approved_artifacts():
    provider = FakeProvider([json.dumps(VALID_DESIGN)])
    context = AgentContext(project_id=9, user_request="Design it.", prior_artifacts={"requirements": {}})
    with pytest.raises(AgentExecutionError, match="Approved requirements and architecture"):
        UIUXDesigner(provider).run(context)
    assert provider.calls == []


def test_uiux_designer_retries_once_then_stops():
    provider = FakeProvider(["not-json", json.dumps(VALID_DESIGN)])
    result = UIUXDesigner(provider).run(make_context())
    assert len(provider.calls) == 2
    assert result.status == "needs_review"


def test_uiux_designer_stops_after_two_invalid_responses():
    provider = FakeProvider(["bad", "still bad"])
    with pytest.raises(AgentExecutionError, match="after 2 attempts"):
        UIUXDesigner(provider).run(make_context())
    assert len(provider.calls) == 2

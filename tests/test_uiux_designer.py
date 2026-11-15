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


def test_uiux_designer_normalizes_structured_personas_without_losing_details():
    design = dict(VALID_DESIGN)
    design["personas"] = [
        {
            "name": "Customer",
            "description": "A shopper comparing products.",
            "goals": ["Find suitable products", "Complete checkout"],
            "pain_points": ["Unclear order status", "Confusing filters"],
        },
        {
            "name": "Site Administrator",
            "responsibilities": ["Manage catalogue", "Monitor inventory"],
            "needs": ["Clear navigation", "Fast access to reports"],
        },
    ]
    provider = FakeProvider([json.dumps(design)])
    result = UIUXDesigner(provider).run(make_context())
    personas = result.artifact["uiux_design"]["personas"]
    assert len(personas) == 2
    assert personas[0].startswith("Customer")
    assert "Unclear order status" in personas[0]
    assert "Complete checkout" in personas[0]
    assert personas[1].startswith("Site Administrator")
    assert "Monitor inventory" in personas[1]


def test_uiux_persona_normalizer_accepts_strings_and_none():
    from forgeai.agents.contracts import UIUXDesignDocument

    design = dict(VALID_DESIGN)
    design["personas"] = ["Customer", {"name": "Admin", "goals": ["Manage users"]}]
    parsed = UIUXDesignDocument.model_validate(design)
    assert parsed.personas[0] == "Customer"
    assert parsed.personas[1].startswith("Admin")
    design["personas"] = None
    assert UIUXDesignDocument.model_validate(design).personas == []


def test_uiux_designer_repairs_missing_comma_in_model_json():
    valid = json.dumps(VALID_DESIGN)
    malformed = valid.replace('", "design_goals":', '" "design_goals":', 1)
    provider = FakeProvider([malformed])
    result = UIUXDesigner(provider).run(make_context())
    assert result.artifact["uiux_design"]["design_goals"] == VALID_DESIGN["design_goals"]



def test_uiux_designer_normalizes_structured_navigation_and_layout_regions():
    design = dict(VALID_DESIGN)
    design["navigation_structure"] = [
        {
            "label": "Main Navigation",
            "children": [
                {"label": "Home", "route": "/"},
                {
                    "label": "Admin",
                    "route": "/admin",
                    "children": [{"label": "Promotions", "route": "/admin/promotions"}],
                },
            ],
        }
    ]
    screen = dict(VALID_DESIGN["screen_specifications"][0])
    screen["layout_regions"] = [
        {"region": "header", "content": "Logo, search and account controls"},
        {"region": "main", "content": "Product listing and filters"},
    ]
    design["screen_specifications"] = [screen]
    provider = FakeProvider([json.dumps(design)])
    result = UIUXDesigner(provider).run(make_context())
    artifact = result.artifact["uiux_design"]
    navigation = " ".join(artifact["navigation_structure"])
    assert "Main Navigation" in navigation
    assert "Promotions" in navigation
    assert "/admin/promotions" in navigation
    regions = " ".join(artifact["screen_specifications"][0]["layout_regions"])
    assert "header" in regions.lower()
    assert "Logo, search and account controls" in regions


def test_uiux_text_list_normalizer_preserves_nested_object_details():
    from forgeai.agents.contracts import UIUXDesignDocument

    design = dict(VALID_DESIGN)
    design["navigation_structure"] = [{"label": "Catalog", "route": "/catalog", "children": [{"label": "Offers", "route": "/offers"}]}]
    parsed = UIUXDesignDocument.model_validate(design)
    assert "Catalog" in parsed.navigation_structure[0]
    assert "/catalog" in parsed.navigation_structure[0]
    assert "Offers" in parsed.navigation_structure[0]
    assert "/offers" in parsed.navigation_structure[0]

def test_uiux_designer_normalizes_scalar_accessibility_notes():
    design = dict(VALID_DESIGN)
    design["reusable_components"] = [
        {
            "component_name": "Search field",
            "purpose": "Search the product catalogue.",
            "behaviour": "Accepts a query and submits on Enter.",
            "accessibility_notes": "Labelled with 'Search products' and supports keyboard focus.",
        },
        {
            "component_name": "Filter accordion",
            "purpose": "Expand and collapse product filters.",
            "behaviour": "Toggles filter options.",
            "accessibility_notes": ["Uses button semantics and exposes expanded state."],
        },
    ]
    provider = FakeProvider([json.dumps(design)])
    result = UIUXDesigner(provider).run(make_context())
    notes = result.artifact["uiux_design"]["reusable_components"]
    assert notes[0]["accessibility_notes"] == [
        "Labelled with 'Search products' and supports keyboard focus."
    ]
    assert notes[1]["accessibility_notes"] == [
        "Uses button semantics and exposes expanded state."
    ]

def test_uiux_designer_normalizes_grouped_navigation_object():
    design = dict(VALID_DESIGN)
    design["navigation_structure"] = {
        "top_level": [
            {"label": "Home", "route": "/"},
            {"label": "Shop", "route": "/shop"},
        ],
        "admin": {"items": [{"label": "Admin Dashboard", "route": "/admin"}]},
    }
    provider = FakeProvider([json.dumps(design)])
    result = UIUXDesigner(provider).run(make_context())
    navigation = " ".join(result.artifact["uiux_design"]["navigation_structure"])
    assert "Top Level" in navigation
    assert "Home" in navigation
    assert "/shop" in navigation
    assert "Admin Dashboard" in navigation
    assert "/admin" in navigation


def test_uiux_designer_accepts_alternate_screen_and_design_system_keys():
    design = dict(VALID_DESIGN)
    design.pop("screen_specifications")
    design["screens"] = [{
        "name": "Product Listing",
        "description": "Browse and filter products.",
        "persona": "Customer",
        "layout": [{"region": "main", "content": "Product grid"}],
        "components": ["Filter panel", "Product card"],
        "primary_cta": "Open product details",
        "states": ["Loading", "Results", "No results"],
        "validation": ["Filter values must be valid."],
    }]
    design.pop("design_system")
    design["visual_design_system"] = {
        "color_palette": ["Primary blue", "Neutral background"],
        "typography": ["16px body", "24px heading"],
        "spacing": ["8px base spacing"],
        "principles": ["Clear hierarchy", "Consistent feedback"],
    }
    provider = FakeProvider([json.dumps(design)])
    result = UIUXDesigner(provider).run(make_context())
    artifact = result.artifact["uiux_design"]
    assert artifact["screen_specifications"][0]["screen_name"] == "Product Listing"
    assert "Product grid" in artifact["screen_specifications"][0]["layout_regions"][0]
    assert "Primary blue" in artifact["design_system"]["colour_tokens"][0]
    assert "8px base spacing" in artifact["design_system"]["spacing_and_layout_rules"][0]
    assert not any("omitted screen specifications" in warning for warning in result.warnings)
    assert not any("omitted the design system" in warning for warning in result.warnings)


def test_uiux_designer_flags_fallback_when_screens_and_design_system_are_omitted():
    design = dict(VALID_DESIGN)
    design.pop("screen_specifications")
    design.pop("design_system")
    provider = FakeProvider([json.dumps(design)])
    result = UIUXDesigner(provider).run(make_context())
    artifact = result.artifact["uiux_design"]
    assert artifact["screen_specifications"][0]["screen_name"] == "Primary Experience — draft fallback"
    assert artifact["design_system"]["colour_tokens"] == []
    assert any("omitted screen specifications" in warning for warning in result.warnings)
    assert any("omitted the design system" in warning for warning in result.warnings)

def test_uiux_designer_preserves_component_variants_and_extra_metadata():
    design = dict(VALID_DESIGN)
    design["reusable_components"] = [
        {
            "component_name": "Product search",
            "purpose": "Search the catalogue.",
            "behaviour": "Filters products by the entered query.",
            "variants": ["with_clear_button", "compact_version"],
            "accessibility_notes": ["Has an accessible name and visible focus."],
            "interaction_states": ["idle", "typing", "results", "empty"],
        },
        {
            "component_name": "Product filter",
            "purpose": "Narrow the product listing.",
            "behaviour": "Applies selected filters.",
            "variants": ["with_clear_all", "single_selection"],
        },
    ]
    provider = FakeProvider([json.dumps(design)])
    result = UIUXDesigner(provider).run(make_context())
    components = result.artifact["uiux_design"]["reusable_components"]
    assert components[0]["variants"] == ["with_clear_button", "compact_version"]
    assert components[1]["variants"] == ["with_clear_all", "single_selection"]
    assert components[0]["interaction_states"] == ["idle", "typing", "results", "empty"]


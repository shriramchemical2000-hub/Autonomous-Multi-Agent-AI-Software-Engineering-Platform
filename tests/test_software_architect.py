import json

import pytest

from forgeai.agents.contracts import AgentContext
from forgeai.agents.software_architect import AgentExecutionError, SoftwareArchitect


VALID_ARCHITECTURE = {
    "system_overview": "A modular web application with a browser client and API service.",
    "components": [
        {
            "name": "Web Client",
            "responsibility": "Presents the user interface.",
            "technology": "React",
            "dependencies": ["API Service"],
        },
        {
            "name": "API Service",
            "responsibility": "Validates requests and applies business rules.",
            "technology": "FastAPI",
            "dependencies": ["Relational Database"],
        },
    ],
    "data_entities": ["User", "Appointment"],
    "api_endpoints": [
        {
            "method": "GET",
            "path": "/api/appointments",
            "purpose": "List appointments for the authenticated user.",
            "authentication_required": True,
        }
    ],
    "security_considerations": ["Enforce authorization on every user-owned record."],
    "design_decisions": ["Use a modular monolith initially to reduce operational overhead."],
    "unresolved_risks": ["Expected peak traffic has not been specified."],
}


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, *, system_prompt, user_prompt, temperature=0.2):
        self.calls.append(user_prompt)
        return self.responses.pop(0)


def test_architect_generates_validated_design_from_requirements():
    provider = FakeProvider([json.dumps(VALID_ARCHITECTURE)])
    context = AgentContext(
        project_id=7,
        user_request="Design the approved product.",
        prior_artifacts={
            "requirements": {
                "product_name": "Appointment Platform",
                "functional_requirements": [{"requirement_id": "FR-001", "title": "Book appointment"}],
            }
        },
    )

    result = SoftwareArchitect(provider).run(context)

    assert result.status == "needs_review"
    assert result.agent_name == "Software Architect"
    assert len(result.artifact["architecture"]["components"]) == 2
    assert "Appointment Platform" in provider.calls[0]
    assert result.warnings


def test_architect_rejects_missing_requirements_before_model_call():
    provider = FakeProvider([json.dumps(VALID_ARCHITECTURE)])
    context = AgentContext(project_id=7, user_request="Design it.")

    with pytest.raises(AgentExecutionError, match="approved requirements"):
        SoftwareArchitect(provider).run(context)

    assert provider.calls == []


def test_architect_retries_once_for_invalid_json():
    provider = FakeProvider(["not-json", json.dumps(VALID_ARCHITECTURE)])
    context = AgentContext(
        project_id=7,
        user_request="Design it.",
        prior_artifacts={"requirements": {"product_name": "Demo"}},
    )

    result = SoftwareArchitect(provider).run(context)

    assert result.status == "needs_review"
    assert len(provider.calls) == 2
    assert "failed the required JSON contract" in provider.calls[1]


def test_architect_stops_after_two_invalid_responses():
    provider = FakeProvider(["bad", "still bad"])
    context = AgentContext(
        project_id=7,
        user_request="Design it.",
        prior_artifacts={"requirements": {"product_name": "Demo"}},
    )

    with pytest.raises(AgentExecutionError, match="after 2 attempts"):
        SoftwareArchitect(provider).run(context)

    assert len(provider.calls) == 2


def test_architect_normalizes_scalar_security_and_design_notes():
    architecture = dict(VALID_ARCHITECTURE)
    architecture["security_considerations"] = (
        "All passwords are hashed; authorization is enforced on state-changing endpoints."
    )
    architecture["design_decisions"] = (
        "Selected modular monolith architecture with asynchronous workers for report generation."
    )
    provider = FakeProvider([json.dumps(architecture)])
    context = AgentContext(
        project_id=7,
        user_request="Design the approved product.",
        prior_artifacts={"requirements": {"product_name": "Appointment Platform"}},
    )

    result = SoftwareArchitect(provider).run(context)
    design = result.artifact["architecture"]

    assert design["security_considerations"] == [
        "All passwords are hashed; authorization is enforced on state-changing endpoints."
    ]
    assert design["design_decisions"] == [
        "Selected modular monolith architecture with asynchronous workers for report generation."
    ]


def test_architect_normalizes_scalar_risks_and_proposed_decisions_alias():
    architecture = dict(VALID_ARCHITECTURE)
    architecture["unresolved_risks"] = (
        "Payment gateway integration remains subject to provider approval before production deployment."
    )
    architecture.pop("design_decisions")
    architecture["proposed_decisions"] = (
        "For monolithic versus microservices, begin with a modular monolith and retain microservices as a future extension."
    )
    provider = FakeProvider([json.dumps(architecture)])
    context = AgentContext(
        project_id=7,
        user_request="Design the approved product.",
        prior_artifacts={"requirements": {"product_name": "Appointment Platform"}},
    )

    result = SoftwareArchitect(provider).run(context)
    design = result.artifact["architecture"]

    assert design["unresolved_risks"] == [
        "Payment gateway integration remains subject to provider approval before production deployment."
    ]
    assert design["design_decisions"] == [
        "For monolithic versus microservices, begin with a modular monolith and retain microservices as a future extension."
    ]

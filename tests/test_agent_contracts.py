import pytest
from pydantic import ValidationError

from forgeai.agents.contracts import (
    AgentContext,
    AgentResult,
    ArchitectureDocument,
    RequirementsDocument,
)


def test_agent_context_has_safe_empty_defaults():
    context = AgentContext(project_id=7, user_request="Build a clinic booking app")
    assert context.constraints == []
    assert context.prior_artifacts == {}


def test_agent_result_rejects_unknown_status():
    with pytest.raises(ValidationError):
        AgentResult(agent_name="QA", status="maybe", summary="Not a valid status")


def test_requirements_document_validates_structured_output():
    doc = RequirementsDocument(
        product_name="Clinic Booking",
        problem_statement="Patients need to book appointments online.",
        target_users=["Patients", "Receptionists"],
        functional_requirements=[
            {
                "requirement_id": "FR-001",
                "title": "Book appointment",
                "description": "A patient can select an available slot.",
                "priority": "must",
                "acceptance_criteria": ["Only available slots can be selected."],
            }
        ],
    )
    assert doc.functional_requirements[0].priority == "must"


def test_architecture_document_rejects_invalid_http_method():
    with pytest.raises(ValidationError):
        ArchitectureDocument(
            system_overview="A web application",
            api_endpoints=[{"method": "CONNECT", "path": "/x", "purpose": "invalid"}],
        )

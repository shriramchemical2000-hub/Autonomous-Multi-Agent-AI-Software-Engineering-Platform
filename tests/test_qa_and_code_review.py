import json

import pytest
from pydantic import ValidationError

from forgeai.agents.contracts import AgentContext, QATestPlan, CodeReviewDocument
from forgeai.agents.qa_engineer import QAEngineer, AgentExecutionError as QAError
from forgeai.agents.code_reviewer import CodeReviewer, AgentExecutionError as ReviewError
from forgeai.orchestration.workflow import build_forge_workflow


REQ = {
    "product_name": "Task Tracker",
    "functional_requirements": [
        {"requirement_id": "FR-01", "title": "Create task", "description": "A user can create a task."}
    ],
}
BUNDLE = {
    "implementation_summary": "Task API",
    "implementation_notes": [],
    "files": [{"path": "src/tasks.py", "language": "python", "purpose": "Task service",
               "content": "def create_task(title):\n    if not title:\n        raise ValueError('title required')\n    return {'title': title}\n"}],
}
PLAN = {
    "plan_summary": "Risk-based task tests.",
    "test_scope": ["Task creation and validation"],
    "test_cases": [{
        "test_id": "TC-01", "title": "Create valid task", "objective": "Verify task creation.",
        "related_requirement_ids": ["FR-01"], "test_type": "unit", "priority": "high",
        "preconditions": [], "steps": ["Submit a non-empty title."],
        "expected_result": "A task is returned with the supplied title.",
        "automation_candidate": True
    }],
    "coverage_gaps": ["No persistence layer is present in the submitted source."],
    "execution_status": "not_executed"
}
REVIEW = {
    "review_summary": "One input validation risk was identified.",
    "verdict": "changes_required",
    "findings": [{
        "finding_id": "CR-01", "severity": "medium", "category": "Input validation",
        "file_path": "src/tasks.py", "line_start": 1, "line_end": 3,
        "issue": "Whitespace-only titles are accepted.",
        "impact": "Users can create visually empty task names.",
        "recommendation": "Reject titles whose stripped value is empty.",
        "confidence": "high"
    }],
    "reviewed_files": ["src/tasks.py"],
    "limitations": ["No runtime tests or dependency audit were performed."]
}


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, *, system_prompt, user_prompt, temperature=0.2):
        self.calls.append(user_prompt)
        return self.responses.pop(0)


def context(prior=None):
    return AgentContext(project_id=7, user_request="Review this implementation.",
                        prior_artifacts=prior or {"requirements": REQ, "code_bundle": BUNDLE})


def test_qa_engineer_creates_unexecuted_traceable_plan():
    provider = FakeProvider([json.dumps(PLAN)])
    result = QAEngineer(provider).run(context())
    assert result.status == "needs_review"
    plan = result.artifact["qa_test_plan"]
    assert plan["execution_status"] == "not_executed"
    assert plan["test_cases"][0]["related_requirement_ids"] == ["FR-01"]
    assert "not been performed" in result.summary


def test_qa_engineer_requires_requirements_and_bundle():
    provider = FakeProvider([json.dumps(PLAN)])
    with pytest.raises(QAError, match="approved requirements"):
        QAEngineer(provider).run(context({"requirements": REQ}))
    assert provider.calls == []


def test_code_reviewer_rejects_finding_for_unknown_file():
    payload = json.loads(json.dumps(REVIEW))
    payload["findings"][0]["file_path"] = "missing.py"
    provider = FakeProvider([json.dumps(payload), json.dumps(payload)])
    with pytest.raises(ReviewError, match="failed validation"):
        CodeReviewer(provider).run(context())
    assert len(provider.calls) == 2


def test_code_reviewer_returns_structured_findings():
    provider = FakeProvider([json.dumps(REVIEW)])
    result = CodeReviewer(provider).run(context())
    review = result.artifact["code_review"]
    assert review["verdict"] == "changes_required"
    assert review["findings"][0]["file_path"] == "src/tasks.py"


def test_review_contract_rejects_incomplete_line_range():
    payload = dict(REVIEW)
    payload["findings"] = [dict(REVIEW["findings"][0], line_end=None)]
    with pytest.raises(ValidationError):
        CodeReviewDocument.model_validate(payload)


def test_qa_workflow_requires_approved_source_bundle_before_model_call():
    provider = FakeProvider([json.dumps(PLAN)])
    with pytest.raises(ValueError, match="approved source bundle"):
        build_forge_workflow(provider).invoke({
            "project_id": 7, "user_request": "Test it.", "requested_stage": "qa",
            "requirements": REQ, "requirements_approved": True,
            "code_bundle": BUNDLE, "code_bundle_approved": False
        })
    assert provider.calls == []


def test_qa_workflow_runs_after_approval_and_stops_for_review():
    provider = FakeProvider([json.dumps(PLAN)])
    result = build_forge_workflow(provider).invoke({
        "project_id": 7, "user_request": "Test it.", "requested_stage": "qa",
        "requirements": REQ, "requirements_approved": True,
        "code_bundle": BUNDLE, "code_bundle_approved": True
    })
    assert result["qa_test_plan"]["execution_status"] == "not_executed"
    assert result["status"] == "awaiting_human_approval"


def test_code_review_workflow_requires_approved_bundle():
    provider = FakeProvider([json.dumps(REVIEW)])
    with pytest.raises(ValueError, match="approved source bundle"):
        build_forge_workflow(provider).invoke({
            "project_id": 7, "user_request": "Review it.", "requested_stage": "review",
            "requirements": REQ, "requirements_approved": True,
            "code_bundle": BUNDLE, "code_bundle_approved": False
        })
    assert provider.calls == []


def test_code_review_workflow_runs_after_approval():
    provider = FakeProvider([json.dumps(REVIEW)])
    result = build_forge_workflow(provider).invoke({
        "project_id": 7, "user_request": "Review it.", "requested_stage": "review",
        "requirements": REQ, "requirements_approved": True,
        "code_bundle": BUNDLE, "code_bundle_approved": True
    })
    assert result["code_review"]["verdict"] == "changes_required"
    assert result["status"] == "awaiting_human_approval"

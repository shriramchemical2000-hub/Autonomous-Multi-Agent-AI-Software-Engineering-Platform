"""Shared typed state for the coordinated ForgeAI workflow."""
from typing import Any, TypedDict


class ForgeWorkflowState(TypedDict, total=False):
    project_id: int
    user_request: str
    constraints: list[str]
    requested_stage: str
    requirements: dict[str, Any]
    requirements_approved: bool
    architecture: dict[str, Any]
    architecture_approved: bool
    uiux_design: dict[str, Any]
    uiux_approved: bool
    code_bundle: dict[str, Any]
    code_bundle_approved: bool
    qa_test_plan: dict[str, Any]
    code_review: dict[str, Any]
    execution_report: dict[str, Any]
    repair_proposal: dict[str, Any]
    repair_attempt: int
    repair_authorized: bool
    task_plan: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    test_results: list[dict[str, Any]]
    review_findings: list[dict[str, Any]]
    approvals: dict[str, bool]
    messages: list[dict[str, str]]
    current_stage: str
    status: str
    summary: str
    warnings: list[str]
    error: str

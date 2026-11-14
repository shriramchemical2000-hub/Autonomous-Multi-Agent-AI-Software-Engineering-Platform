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

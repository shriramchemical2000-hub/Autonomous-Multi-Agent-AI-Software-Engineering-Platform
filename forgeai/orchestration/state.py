"""Typed shared state for the planned multi-agent workflow."""
from typing import Any, TypedDict


class ForgeWorkflowState(TypedDict, total=False):
    project_id: int
    user_request: str
    requirements: dict[str, Any]
    architecture: dict[str, Any]
    task_plan: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    test_results: list[dict[str, Any]]
    review_findings: list[dict[str, Any]]
    approvals: dict[str, bool]
    messages: list[dict[str, str]]
    current_stage: str
    status: str
    error: str

"""Pydantic contracts shared by specialist agents."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: int
    user_request: str = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    prior_artifacts: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str = Field(min_length=1)
    status: Literal["completed", "needs_review", "failed"]
    summary: str = Field(min_length=1)
    artifact: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class RequirementItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_id: str
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    priority: Literal["must", "should", "could", "wont"] = "should"
    acceptance_criteria: list[str] = Field(default_factory=list)


class RequirementsDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_name: str = Field(min_length=1)
    problem_statement: str = Field(min_length=1)
    target_users: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    functional_requirements: list[RequirementItem] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class ArchitectureComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    responsibility: str = Field(min_length=1)
    technology: str | None = None
    dependencies: list[str] = Field(default_factory=list)


class APIEndpoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    authentication_required: bool = True


class ArchitectureDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system_overview: str = Field(min_length=1)
    components: list[ArchitectureComponent] = Field(default_factory=list)
    data_entities: list[str] = Field(default_factory=list)
    api_endpoints: list[APIEndpoint] = Field(default_factory=list)
    security_considerations: list[str] = Field(default_factory=list)
    design_decisions: list[str] = Field(default_factory=list)
    unresolved_risks: list[str] = Field(default_factory=list)

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

    requirement_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    priority: Literal["must", "should", "could", "wont"] = "should"
    acceptance_criteria: list[str] = Field(default_factory=list)


class UserStory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    story_id: str = Field(min_length=1)
    persona: str = Field(min_length=1)
    action: str = Field(min_length=1)
    benefit: str = Field(min_length=1)
    acceptance_criteria: list[str] = Field(default_factory=list)
    related_requirement_ids: list[str] = Field(default_factory=list)


class RequirementsDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_name: str = Field(min_length=1)
    problem_statement: str = Field(min_length=1)
    target_users: list[str] = Field(default_factory=list)
    scope_in: list[str] = Field(default_factory=list)
    scope_out: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    functional_requirements: list[RequirementItem] = Field(default_factory=list)
    user_stories: list[UserStory] = Field(default_factory=list)
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



class UserJourneyStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=1)
    user_action: str = Field(min_length=1)
    system_response: str = Field(min_length=1)
    decision_or_exception: str | None = None


class UserJourney(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    entry_point: str = Field(min_length=1)
    steps: list[UserJourneyStep] = Field(min_length=1)
    success_outcome: str = Field(min_length=1)


class ScreenSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    screen_name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    primary_user: str = Field(min_length=1)
    layout_regions: list[str] = Field(min_length=1)
    key_components: list[str] = Field(default_factory=list)
    primary_action: str = Field(min_length=1)
    states_and_feedback: list[str] = Field(default_factory=list)
    validation_and_errors: list[str] = Field(default_factory=list)


class UIComponentSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    behaviour: str = Field(min_length=1)
    accessibility_notes: list[str] = Field(default_factory=list)


class DesignSystemSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    colour_tokens: list[str] = Field(default_factory=list)
    typography_scale: list[str] = Field(default_factory=list)
    spacing_and_layout_rules: list[str] = Field(default_factory=list)
    visual_principles: list[str] = Field(default_factory=list)


class UIUXDesignDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_overview: str = Field(min_length=1)
    design_goals: list[str] = Field(default_factory=list)
    personas: list[str] = Field(default_factory=list)
    user_journeys: list[UserJourney] = Field(default_factory=list)
    navigation_structure: list[str] = Field(default_factory=list)
    screen_specifications: list[ScreenSpecification] = Field(min_length=1)
    reusable_components: list[UIComponentSpecification] = Field(default_factory=list)
    design_system: DesignSystemSpecification
    responsive_behaviour: list[str] = Field(default_factory=list)
    accessibility_requirements: list[str] = Field(default_factory=list)
    usability_risks: list[str] = Field(default_factory=list)
    open_design_questions: list[str] = Field(default_factory=list)


class GeneratedSourceFile(BaseModel):
    """One plain-text source file; paths are constrained before export."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=180)
    language: str = Field(min_length=1, max_length=40)
    purpose: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=30000)

    @classmethod
    def _validate_safe_path(cls, value: str) -> str:
        import re
        from pathlib import PurePosixPath

        if "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
            raise ValueError("Generated file paths must be relative POSIX paths.")
        parts = value.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError("Generated file paths cannot contain empty, dot, or parent segments.")
        if any(part.startswith(".") for part in parts):
            raise ValueError("Hidden paths are not permitted in generated bundles.")
        allowed_suffixes = {".py", ".html", ".css", ".js", ".ts", ".tsx", ".jsx", ".json", ".md", ".yaml", ".yml", ".toml"}
        suffix = PurePosixPath(value).suffix.lower()
        if suffix not in allowed_suffixes:
            raise ValueError(f"Unsupported generated file type: {suffix or 'no extension'}.")
        if len(parts) > 6:
            raise ValueError("Generated file path is nested too deeply.")
        return value

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        model = super().model_validate(obj, *args, **kwargs)
        model.path = cls._validate_safe_path(model.path)
        return model


class CodeGenerationDocument(BaseModel):
    """A bounded, reviewable collection of generated text source files."""

    model_config = ConfigDict(extra="forbid")

    implementation_summary: str = Field(min_length=1)
    implementation_notes: list[str] = Field(default_factory=list)
    files: list[GeneratedSourceFile] = Field(min_length=1, max_length=30)

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        model = super().model_validate(obj, *args, **kwargs)
        paths = [item.path for item in model.files]
        if len(paths) != len(set(paths)):
            raise ValueError("Generated bundle contains duplicate file paths.")
        total_bytes = sum(len(item.content.encode("utf-8")) for item in model.files)
        if total_bytes > 200_000:
            raise ValueError("Generated bundle exceeds the 200 KB text limit.")
        return model

"""Pydantic contracts shared by specialist agents."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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

    @field_validator("non_functional_requirements", mode="before")
    @classmethod
    def normalize_non_functional_requirements(cls, value: Any) -> Any:
        """Accept concise strings or structured NFR objects from model providers.

        The UI and downstream agents consume a stable list of readable strings.
        Preserve structured detail instead of failing the whole artifact when a
        model returns {title, description, acceptance_criteria} objects.
        """
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        normalized: list[Any] = []
        for item in value:
            if isinstance(item, str):
                normalized.append(item)
            elif isinstance(item, dict):
                parts: list[str] = []
                title = item.get("title") or item.get("name")
                description = item.get("description") or item.get("requirement")
                category = item.get("category") or item.get("type")
                if category:
                    parts.append(f"{category}:")
                if title:
                    parts.append(str(title))
                if description:
                    parts.append(str(description))
                criteria = item.get("acceptance_criteria") or item.get("criteria") or []
                if isinstance(criteria, str):
                    criteria = [criteria]
                if isinstance(criteria, list) and criteria:
                    parts.append("Acceptance criteria: " + "; ".join(str(c) for c in criteria))
                # Retain any additional model-provided detail without leaking
                # arbitrary nested objects into the rendered specification.
                known = {"title", "name", "description", "requirement", "category", "type",
                         "acceptance_criteria", "criteria"}
                for key, detail in item.items():
                    if key not in known and detail not in (None, "", [], {}):
                        parts.append(f"{key.replace('_', ' ').title()}: {detail}")
                normalized.append(" — ".join(parts) if parts else str(item))
            else:
                normalized.append(item)
        return normalized


    @field_validator("open_questions", mode="before")
    @classmethod
    def normalize_open_questions(cls, value: Any) -> Any:
        """Accept plain questions or structured question objects from model providers."""
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        normalized: list[Any] = []
        for item in value:
            if isinstance(item, str):
                normalized.append(item)
            elif isinstance(item, dict):
                question = item.get("question") or item.get("title") or item.get("text")
                if question:
                    details = [str(question)]
                    for key, detail in item.items():
                        if key not in {"question", "title", "text"} and detail not in (None, "", [], {}):
                            details.append(f"{key.replace('_', ' ').title()}: {detail}")
                    normalized.append(" — ".join(details))
                else:
                    normalized.append("; ".join(
                        f"{key.replace('_', ' ').title()}: {detail}"
                        for key, detail in item.items()
                        if detail not in (None, "", [], {})
                    ) or str(item))
            else:
                normalized.append(item)
        return normalized


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

    @model_validator(mode="before")
    @classmethod
    def normalize_architecture_aliases(cls, value: Any) -> Any:
        """Map provider-specific decision naming into the canonical contract."""
        if not isinstance(value, dict) or "proposed_decisions" not in value:
            return value
        normalized = dict(value)
        proposed = normalized.pop("proposed_decisions")
        existing = normalized.get("design_decisions", [])
        if existing is None:
            existing = []
        if isinstance(existing, str):
            existing = [existing] if existing.strip() else []
        elif not isinstance(existing, list):
            return normalized
        if isinstance(proposed, str):
            proposed = [proposed] if proposed.strip() else []
        elif proposed is None:
            proposed = []
        if isinstance(proposed, list):
            normalized["design_decisions"] = existing + proposed
        return normalized

    @field_validator(
        "security_considerations", "design_decisions", "unresolved_risks",
        mode="before",
    )
    @classmethod
    def normalize_architecture_text_lists(cls, value: Any) -> Any:
        """Accept either a list of design notes or one consolidated text value."""
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        return value


def _render_ui_detail(value: Any) -> str:
    """Render nested UI/navigation objects as readable text without losing details."""
    if isinstance(value, dict):
        label = value.get("label") or value.get("name") or value.get("region") or value.get("title")
        route = value.get("route") or value.get("path") or value.get("url")
        parts: list[str] = []
        if label:
            parts.append(str(label))
        if route:
            parts.append(f"({route})")
        for key, detail in value.items():
            if key in {"label", "name", "region", "title", "route", "path", "url"} or detail in (None, "", [], {}):
                continue
            rendered = _render_ui_detail(detail)
            if rendered:
                parts.append(f"{key.replace('_', ' ').title()}: {rendered}")
        return " — ".join(parts) if parts else str(value)
    if isinstance(value, list):
        return "; ".join(_render_ui_detail(item) for item in value if item not in (None, "", [], {}))
    return str(value)


def _normalize_ui_text_list(value: Any) -> Any:
    """Normalize scalar, object, and array values into readable text arrays."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, dict):
        return [_render_ui_detail(value)]
    if not isinstance(value, list):
        return [str(value)]
    return [
        item if isinstance(item, str) else _render_ui_detail(item)
        for item in value
    ]


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

    @model_validator(mode="before")
    @classmethod
    def normalize_screen_aliases(cls, value: Any) -> Any:
        """Map common provider naming variants into the stable screen contract."""
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        aliases = {
            "screen_name": ("name", "title", "page_name", "screen", "page"),
            "purpose": ("description", "screen_purpose", "goal"),
            "primary_user": ("persona", "primary_persona", "user", "audience"),
            "layout_regions": ("layout", "regions", "sections", "content_regions"),
            "key_components": ("components", "ui_components", "elements"),
            "primary_action": ("primary_cta", "main_action", "call_to_action", "cta"),
            "states_and_feedback": ("states", "feedback_states", "ui_states"),
            "validation_and_errors": ("validation", "errors", "error_handling"),
        }
        for target, candidates in aliases.items():
            if target not in normalized:
                for candidate in candidates:
                    if candidate in normalized:
                        normalized[target] = normalized.pop(candidate)
                        break
        # Some providers return extra descriptive metadata; preserve it in the
        # screen purpose instead of letting harmless metadata invalidate the design.
        known = set(aliases) | {alias for group in aliases.values() for alias in group}
        extra_details = []
        for key in list(normalized):
            if key not in known:
                detail = normalized.pop(key)
                if detail not in (None, "", [], {}):
                    extra_details.append(f"{key.replace('_', ' ').title()}: {_render_ui_detail(detail)}")
        if extra_details:
            existing = normalized.get("purpose", "Screen experience")
            normalized["purpose"] = str(existing) + " " + "; ".join(extra_details)
        return normalized

    @field_validator("layout_regions", "key_components", "states_and_feedback", "validation_and_errors", mode="before")
    @classmethod
    def normalize_screen_detail_lists(cls, value: Any) -> Any:
        return _normalize_ui_text_list(value)


class UIComponentSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    behaviour: str = Field(min_length=1)
    accessibility_notes: list[str] = Field(default_factory=list)

    @field_validator("accessibility_notes", mode="before")
    @classmethod
    def normalize_accessibility_notes(cls, value: Any) -> Any:
        return _normalize_ui_text_list(value)


class DesignSystemSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    colour_tokens: list[str] = Field(default_factory=list)
    typography_scale: list[str] = Field(default_factory=list)
    spacing_and_layout_rules: list[str] = Field(default_factory=list)
    visual_principles: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_design_system_aliases(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"visual_principles": [value]}
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        aliases = {
            "colour_tokens": ("color_tokens", "colors", "colours", "color_palette", "palette"),
            "typography_scale": ("typography", "type_scale", "font_scale"),
            "spacing_and_layout_rules": ("spacing", "layout_rules", "spacing_rules", "grid_rules"),
            "visual_principles": ("principles", "visual_direction", "design_principles"),
        }
        for target, candidates in aliases.items():
            if target not in normalized:
                for candidate in candidates:
                    if candidate in normalized:
                        normalized[target] = normalized.pop(candidate)
                        break
        # The design system is descriptive; fold noncanonical token groups into
        # the closest canonical field rather than discarding useful model detail.
        known = set(aliases) | {alias for group in aliases.values() for alias in group}
        extra = []
        for key in list(normalized):
            if key not in known:
                detail = normalized.pop(key)
                if detail not in (None, "", [], {}):
                    extra.append(f"{key.replace('_', ' ').title()}: {_render_ui_detail(detail)}")
        if extra:
            normalized.setdefault("visual_principles", [])
            current = normalized["visual_principles"]
            if isinstance(current, str):
                current = [current]
            normalized["visual_principles"] = list(current or []) + extra
        return normalized

    @field_validator("colour_tokens", "typography_scale", "spacing_and_layout_rules", "visual_principles", mode="before")
    @classmethod
    def normalize_design_system_lists(cls, value: Any) -> Any:
        return _normalize_ui_text_list(value)


class UIUXDesignDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def normalize_document_shape(cls, value: Any) -> Any:
        """Accept common alternate top-level UI/UX response shapes."""
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        aliases = {
            "design_overview": ("overview", "design_summary", "experience_overview", "ux_overview"),
            "design_goals": ("goals", "experience_goals", "ux_goals"),
            "user_journeys": ("journeys", "customer_journeys", "experience_flows"),
            "navigation_structure": ("navigation", "navigation_map", "navigation_tree", "site_map", "sitemap"),
            "screen_specifications": ("screens", "screen_specs", "screen_designs", "pages", "page_specifications", "ui_screens"),
            "reusable_components": ("components", "ui_components", "component_library"),
            "design_system": ("visual_design_system", "design_tokens", "style_guide", "visual_system"),
            "responsive_behaviour": ("responsive_behavior", "responsive_design", "breakpoint_behaviour"),
            "accessibility_requirements": ("accessibility", "accessibility_standards"),
            "usability_risks": ("usability_concerns", "ux_risks"),
            "open_design_questions": ("design_questions", "open_questions"),
        }
        for target, candidates in aliases.items():
            if target not in normalized:
                for candidate in candidates:
                    if candidate in normalized:
                        normalized[target] = normalized.pop(candidate)
                        break

        navigation = normalized.get("navigation_structure")
        if isinstance(navigation, dict):
            # Navigation is often represented as {top_level: [], footer: [], ...}.
            # Keep each group label and all nested labels/routes in the text output.
            normalized["navigation_structure"] = [
                {"label": section.replace("_", " ").title(), "items": entries}
                for section, entries in navigation.items()
                if entries not in (None, "", [], {})
            ]

        screens = normalized.get("screen_specifications")
        if isinstance(screens, dict):
            # Also accept a map keyed by screen name, e.g. {"Home": {...}}.
            converted = []
            for name, details in screens.items():
                if isinstance(details, dict):
                    item = dict(details)
                    item.setdefault("screen_name", str(name))
                    converted.append(item)
                else:
                    converted.append({"screen_name": str(name), "purpose": _render_ui_detail(details),
                                      "primary_user": "Primary user", "layout_regions": ["Main content"],
                                      "primary_action": "Complete the primary task"})
            normalized["screen_specifications"] = converted
        return normalized

    design_overview: str = Field(min_length=1)
    design_goals: list[str] = Field(default_factory=list)
    personas: list[str] = Field(default_factory=list)

    @field_validator("personas", mode="before")
    @classmethod
    def normalize_personas(cls, value: Any) -> Any:
        """Convert structured persona objects into readable, information-preserving text."""
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        normalized: list[Any] = []
        for item in value:
            if isinstance(item, str):
                normalized.append(item)
            elif isinstance(item, dict):
                parts: list[str] = []
                name = item.get("name") or item.get("persona") or item.get("title") or item.get("role")
                if name:
                    parts.append(str(name))
                for key, detail in item.items():
                    if key in {"name", "persona", "title", "role"} or detail in (None, "", [], {}):
                        continue
                    label = key.replace("_", " ").title()
                    if isinstance(detail, list):
                        rendered = "; ".join(str(entry) for entry in detail)
                    elif isinstance(detail, dict):
                        rendered = "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in detail.items())
                    else:
                        rendered = str(detail)
                    parts.append(f"{label}: {rendered}")
                normalized.append(" — ".join(parts) if parts else "Persona details not supplied.")
            else:
                normalized.append(str(item))
        return normalized
    user_journeys: list[UserJourney] = Field(default_factory=list)
    navigation_structure: list[str] = Field(default_factory=list)
    screen_specifications: list[ScreenSpecification] = Field(default_factory=lambda: [
        ScreenSpecification(
            screen_name="Primary Experience — draft fallback",
            purpose="The model omitted screen-level details. This placeholder must be replaced with a product-specific screen specification during human review.",
            primary_user="Primary user",
            layout_regions=["Global header and navigation", "Main task content", "Contextual feedback and primary action"],
            primary_action="Complete the primary task",
        )
    ])
    reusable_components: list[UIComponentSpecification] = Field(default_factory=list)
    design_system: DesignSystemSpecification = Field(default_factory=DesignSystemSpecification)
    responsive_behaviour: list[str] = Field(default_factory=list)
    accessibility_requirements: list[str] = Field(default_factory=list)
    usability_risks: list[str] = Field(default_factory=list)
    open_design_questions: list[str] = Field(default_factory=list)

    @field_validator(
        "design_goals", "navigation_structure", "responsive_behaviour",
        "accessibility_requirements", "usability_risks", "open_design_questions",
        mode="before",
    )
    @classmethod
    def normalize_ui_detail_lists(cls, value: Any) -> Any:
        return _normalize_ui_text_list(value)


class GeneratedSourceFile(BaseModel):
    """One plain-text source file; paths are constrained before export."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=180)
    language: str = Field(min_length=1, max_length=40)
    purpose: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=30000)

    @field_validator("path")
    @classmethod
    def validate_safe_path(cls, value: str) -> str:
        import re
        from pathlib import PurePosixPath

        if "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
            raise ValueError("Generated file paths must be relative POSIX paths.")
        parts = value.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError("Generated file paths cannot contain empty, dot, or parent segments.")
        if any(part.startswith(".") for part in parts):
            raise ValueError("Hidden paths are not permitted in generated bundles.")
        reserved_names = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
        if any(
            ":" in part
            or part.endswith((".", " "))
            or any(ord(character) < 32 for character in part)
            or part.split(".", 1)[0].upper() in reserved_names
            for part in parts
        ):
            raise ValueError("Generated paths contain a Windows-reserved or invalid path segment.")
        allowed_suffixes = {".py", ".html", ".css", ".js", ".ts", ".tsx", ".jsx", ".json", ".md", ".yaml", ".yml", ".toml"}
        suffix = PurePosixPath(value).suffix.lower()
        if suffix not in allowed_suffixes:
            raise ValueError(f"Unsupported generated file type: {suffix or 'no extension'}.")
        if len(parts) > 6:
            raise ValueError("Generated file path is nested too deeply.")
        return value


class CodeGenerationDocument(BaseModel):
    """A bounded, reviewable collection of generated text source files."""

    model_config = ConfigDict(extra="forbid")

    implementation_summary: str = Field(min_length=1)
    implementation_notes: list[str] = Field(default_factory=list)
    files: list[GeneratedSourceFile] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def validate_bundle(self):
        paths = [item.path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("Generated bundle contains duplicate file paths.")
        total_bytes = sum(len(item.content.encode("utf-8")) for item in self.files)
        if total_bytes > 200_000:
            raise ValueError("Generated bundle exceeds the 200 KB text limit.")
        return self



class QATestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    test_id: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1)
    related_requirement_ids: list[str] = Field(default_factory=list)
    test_type: Literal["unit", "integration", "system", "acceptance", "security", "usability"]
    priority: Literal["high", "medium", "low"]
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(min_length=1)
    expected_result: str = Field(min_length=1)
    automation_candidate: bool = False

class QATestPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_summary: str = Field(min_length=1)
    test_scope: list[str] = Field(default_factory=list)
    test_cases: list[QATestCase] = Field(min_length=1, max_length=100)
    coverage_gaps: list[str] = Field(default_factory=list)
    execution_status: Literal["not_executed"]

    @model_validator(mode="after")
    def validate_unique_test_ids(self):
        ids = [case.test_id for case in self.test_cases]
        if len(ids) != len(set(ids)):
            raise ValueError("QA test plan contains duplicate test IDs.")
        return self

class CodeReviewFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str = Field(min_length=1, max_length=40)
    severity: Literal["critical", "high", "medium", "low", "info"]
    category: str = Field(min_length=1, max_length=80)
    file_path: str = Field(min_length=1, max_length=180)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    issue: str = Field(min_length=1)
    impact: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)
    confidence: Literal["high", "medium", "low"]

    @model_validator(mode="after")
    def validate_line_range(self):
        if (self.line_start is None) != (self.line_end is None):
            raise ValueError("Both line_start and line_end must be supplied together.")
        if self.line_start is not None and self.line_end < self.line_start:
            raise ValueError("line_end cannot be before line_start.")
        return self

class CodeReviewDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_summary: str = Field(min_length=1)
    verdict: Literal["approve", "changes_required", "reject"]
    findings: list[CodeReviewFinding] = Field(default_factory=list, max_length=100)
    reviewed_files: list[str] = Field(min_length=1, max_length=30)
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_findings(self):
        ids = [finding.finding_id for finding in self.findings]
        if len(ids) != len(set(ids)):
            raise ValueError("Code review contains duplicate finding IDs.")
        return self



class CodeRepairChange(BaseModel):
    """A full replacement for one existing non-test source file."""

    model_config = ConfigDict(extra="forbid")
    file_path: str = Field(min_length=1, max_length=180)
    replacement_content: str = Field(min_length=1, max_length=30000)
    rationale: str = Field(min_length=1)
    addresses: list[str] = Field(default_factory=list)


class CodeRepairDocument(BaseModel):
    """Bounded repair proposal; it never adds, deletes, or edits test files."""

    model_config = ConfigDict(extra="forbid")
    repair_summary: str = Field(min_length=1)
    changes: list[CodeRepairChange] = Field(min_length=1, max_length=10)
    addressed_findings: list[str] = Field(default_factory=list)
    unresolved_risks: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_repair_paths(self):
        paths = [change.file_path for change in self.changes]
        if len(paths) != len(set(paths)):
            raise ValueError("Repair proposal contains duplicate file paths.")
        return self

"""Executable UI/UX Designer specialist."""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from forgeai.agents.contracts import AgentContext, AgentResult, UIUXDesignDocument
from forgeai.providers.base import ModelProvider


class AgentExecutionError(RuntimeError):
    """Raised when the designer cannot produce a valid design artifact."""


SYSTEM_PROMPT = """You are ForgeAI's senior Product UI/UX Designer.
Create a detailed, implementation-ready experience specification using BOTH the approved
requirements and approved software architecture supplied by the user. Treat them as binding
sources of truth. Do not invent features, roles, screens, integrations, or capabilities that
conflict with either artifact. Explain any necessary assumptions as open design questions.
Design for clarity, task completion, consistency, responsive behaviour, accessibility,
empty/loading/error/success states, validation, and keyboard/screen-reader use.
Create meaningful user journeys, navigation structure, screen-by-screen layout specifications,
reusable UI components, and a coherent design system. Keep the response complete but bounded:
3-5 user journeys, 6-10 screen specifications, and 8-12 reusable components. Use concise,
actionable strings in arrays; avoid repeating the same detail across fields. Make screen
specifications concrete enough for a frontend engineer to implement. Do not output source code
or claim usability testing has occurred.

Return exactly one JSON object and no Markdown fences with keys:
design_overview, design_goals, personas, user_journeys, navigation_structure,
screen_specifications, reusable_components, design_system, responsive_behaviour,
accessibility_requirements, usability_risks, open_design_questions.
Journey fields: persona, goal, entry_point, steps, success_outcome.
Each step: step (integer >= 1), user_action, system_response, decision_or_exception (string or null).
Screen fields: screen_name, purpose, primary_user, layout_regions, key_components,
primary_action, states_and_feedback, validation_and_errors.
Reusable component fields: component_name, purpose, behaviour, accessibility_notes.
design_system fields: colour_tokens, typography_scale, spacing_and_layout_rules, visual_principles.
Do not add keys outside this schema. Provide at least one complete screen specification.
"""


class UIUXDesigner:
    """Create one validated design artifact with at most one correction retry."""

    name = "UI/UX Designer"
    max_attempts = 2

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    @staticmethod
    def _parse_response(raw: str) -> UIUXDesignDocument:
        cleaned = raw.strip()
        match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.IGNORECASE | re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            # Recover common formatting defects without an extra runtime package.
            # Quote unquoted object keys and remove trailing commas only; the
            # strict Pydantic schema below still validates the resulting object.
            repaired = re.sub(
                r'([,{]\s*)([A-Za-z_][A-Za-z0-9_-]*)(\s*:)',
                lambda match: match.group(1) + json.dumps(match.group(2)) + match.group(3),
                cleaned,
            )
            repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
            payload = json.loads(repaired)
        if not isinstance(payload, dict):
            raise ValueError("The model response must contain one JSON object.")
        return UIUXDesignDocument.model_validate(payload)

    def run(self, context: AgentContext) -> AgentResult:
        requirements = context.prior_artifacts.get("requirements")
        architecture = context.prior_artifacts.get("architecture")
        if not isinstance(requirements, dict) or not isinstance(architecture, dict):
            raise AgentExecutionError("Approved requirements and architecture are required before UI/UX design can begin.")
        user_prompt = (
            "APPROVED REQUIREMENTS (source of truth):\n"
            + json.dumps(requirements, ensure_ascii=False, indent=2)
            + "\n\nAPPROVED ARCHITECTURE (source of truth):\n"
            + json.dumps(architecture, ensure_ascii=False, indent=2)
            + "\n\nPROJECT CONSTRAINTS:\n"
            + ("\n".join(f"- {item}" for item in context.constraints) or "- None supplied")
            + "\n\nProduce the complete implementation-ready UI/UX specification."
        )
        correction = ""
        last_error = ""
        for _attempt in range(1, self.max_attempts + 1):
            prompt = user_prompt
            if correction:
                prompt += (
                    "\n\nYour previous response failed the required JSON contract. "
                    f"Correct this issue and return the full JSON object only: {correction}"
                )
            raw = self.provider.generate(system_prompt=SYSTEM_PROMPT, user_prompt=prompt, temperature=0.1)
            try:
                document = self._parse_response(raw)
                warnings = []
                if document.usability_risks:
                    warnings.append(f"{len(document.usability_risks)} usability risk(s) require human review.")
                if document.open_design_questions:
                    warnings.append(f"{len(document.open_design_questions)} design question(s) remain unresolved.")
                return AgentResult(
                    agent_name=self.name,
                    status="needs_review",
                    summary=(
                        f"Specified {len(document.user_journeys)} user journeys, "
                        f"{len(document.screen_specifications)} screens, and "
                        f"{len(document.reusable_components)} reusable UI components. Human review is required."
                    ),
                    artifact={"uiux_design": document.model_dump(mode="json")},
                    warnings=warnings,
                )
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                correction = last_error
        raise AgentExecutionError(
            f"UI/UX Designer could not produce a valid design after {self.max_attempts} attempts. "
            f"Last validation issue: {last_error}"
        )

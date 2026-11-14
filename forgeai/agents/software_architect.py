"""Executable Software Architect specialist."""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from forgeai.agents.contracts import AgentContext, AgentResult, ArchitectureDocument
from forgeai.providers.base import ModelProvider


class AgentExecutionError(RuntimeError):
    """Raised when the architect cannot produce a valid architecture artifact."""


SYSTEM_PROMPT = """You are ForgeAI's senior Software Architect.
Design a practical, secure, maintainable architecture from the APPROVED requirements
specification supplied by the user. Treat that specification as the source of truth.
Do not silently add product features. If a design choice is necessary but not specified,
label it clearly as a proposed decision or unresolved risk. Prefer a modular architecture
appropriate to the stated scale and constraints; do not add microservices without a reason.
Include components with responsibilities, technology choices where justified, dependencies,
data entities, API endpoints, security considerations, design decisions, and unresolved risks.
For API endpoints, use only GET, POST, PUT, PATCH, DELETE and include authentication_required.
Do not claim compliance or production readiness without evidence.

Return exactly one JSON object, no Markdown fences or commentary, with these keys:
system_overview, components, data_entities, api_endpoints, security_considerations,
design_decisions, unresolved_risks.
Each component: name, responsibility, technology (string or null), dependencies (array).
Each endpoint: method, path, purpose, authentication_required (boolean).
Do not add keys outside the schema. Be specific and explain trade-offs in design_decisions.
"""


class SoftwareArchitect:
    """Create one validated architecture artifact with at most one correction retry."""

    name = "Software Architect"
    max_attempts = 2

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    @staticmethod
    def _parse_response(raw: str) -> ArchitectureDocument:
        cleaned = raw.strip()
        match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.IGNORECASE | re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
        payload: Any = json.loads(cleaned)
        return ArchitectureDocument.model_validate(payload)

    def run(self, context: AgentContext) -> AgentResult:
        requirements = context.prior_artifacts.get("requirements")
        if not isinstance(requirements, dict):
            raise AgentExecutionError("An approved requirements specification is required before architecture can begin.")
        user_prompt = (
            "APPROVED REQUIREMENTS SPECIFICATION (source of truth):\n"
            + json.dumps(requirements, ensure_ascii=False, indent=2)
            + "\n\nPROJECT CONSTRAINTS:\n"
            + ("\n".join(f"- {item}" for item in context.constraints) or "- None supplied")
            + "\n\nDesign the architecture for this specification. Return the complete JSON object."
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
                if document.unresolved_risks:
                    warnings.append(f"{len(document.unresolved_risks)} unresolved architecture risk(s) require review.")
                return AgentResult(
                    agent_name=self.name,
                    status="needs_review",
                    summary=(
                        f"Designed {len(document.components)} architecture components, "
                        f"{len(document.api_endpoints)} API endpoints, and "
                        f"{len(document.data_entities)} data entities. Human review is required."
                    ),
                    artifact={"architecture": document.model_dump(mode="json")},
                    warnings=warnings,
                )
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                correction = last_error
        raise AgentExecutionError(
            f"Software Architect could not produce a valid design after {self.max_attempts} attempts. "
            f"Last validation issue: {last_error}"
        )

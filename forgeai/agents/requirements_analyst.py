"""Executable Requirements Analyst specialist."""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from forgeai.agents.contracts import AgentContext, AgentResult, RequirementsDocument
from forgeai.providers.base import ModelProvider


class AgentExecutionError(RuntimeError):
    """Raised when an agent cannot produce a valid, contract-compliant artifact."""


SYSTEM_PROMPT = """You are ForgeAI's senior Requirements Analyst.
Convert the supplied product brief into a precise, implementation-ready requirements
specification. Do not invent facts. Separate explicit brief details from assumptions.
Identify ambiguity as open questions. Make requirements testable and prioritised.
Create user stories linked to requirement IDs. Include measurable non-functional
requirements where the brief supports them; if values are unknown, state the unknown
as an open question rather than inventing a target.

Return exactly one JSON object and no Markdown fences or commentary. Use these keys:
product_name, problem_statement, target_users, scope_in, scope_out, assumptions,
functional_requirements, user_stories, non_functional_requirements, open_questions.
Each functional requirement has: requirement_id, title, description, priority
(must|should|could|wont), acceptance_criteria.
Each user story has: story_id, persona, action, benefit, acceptance_criteria,
related_requirement_ids. Use IDs such as FR-001 and US-001.
Do not include keys outside this schema. Empty arrays are acceptable when information
is genuinely unavailable; explain important gaps in open_questions.
"""


class RequirementsAnalyst:
    """Generate one validated requirements artifact with a maximum of two model calls."""

    name = "Requirements Analyst"
    max_attempts = 2

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    @staticmethod
    def _parse_response(raw: str) -> RequirementsDocument:
        cleaned = raw.strip()
        fence_match = re.fullmatch(
            r"```(?:json)?\s*(.*?)\s*```",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if fence_match:
            cleaned = fence_match.group(1).strip()
        payload: Any = json.loads(cleaned)
        return RequirementsDocument.model_validate(payload)

    def run(self, context: AgentContext) -> AgentResult:
        user_prompt = (
            "PRODUCT BRIEF:\n"
            f"{context.user_request}\n\n"
            "PROJECT CONSTRAINTS:\n"
            + ("\n".join(f"- {item}" for item in context.constraints) or "- None supplied")
            + "\n\nReturn the complete requirements specification as JSON."
        )
        correction = ""
        last_error = ""
        for attempt in range(1, self.max_attempts + 1):
            prompt = user_prompt
            if correction:
                prompt += (
                    "\n\nYour previous response did not satisfy the required JSON contract. "
                    f"Correct this issue and return the full JSON object only: {correction}"
                )
            raw = self.provider.generate(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.1,
            )
            try:
                document = self._parse_response(raw)
                warnings = []
                if document.open_questions:
                    warnings.append(
                        f"{len(document.open_questions)} clarification question(s) require product-owner review."
                    )
                if document.assumptions:
                    warnings.append(
                        f"{len(document.assumptions)} assumption(s) are explicitly identified and should be confirmed."
                    )
                return AgentResult(
                    agent_name=self.name,
                    status="needs_review",
                    summary=(
                        f"Generated {len(document.functional_requirements)} functional requirements, "
                        f"{len(document.user_stories)} user stories, and "
                        f"{len(document.non_functional_requirements)} non-functional requirements. "
                        "Human review is required before downstream design or implementation."
                    ),
                    artifact={"requirements": document.model_dump(mode="json")},
                    warnings=warnings,
                )
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                correction = last_error
        raise AgentExecutionError(
            f"Requirements Analyst could not produce a valid specification after "
            f"{self.max_attempts} attempts. Last validation issue: {last_error}"
        )

"""Approval-gated source code generation specialist."""
from __future__ import annotations

import json
import re

from pydantic import ValidationError

from forgeai.agents.contracts import AgentContext, AgentResult, CodeGenerationDocument
from forgeai.providers.base import ModelProvider


class AgentExecutionError(RuntimeError):
    """Raised when generated source files fail validation."""


SYSTEM_PROMPT = """You are ForgeAI's senior software implementation engineer.
Generate a small but coherent, runnable-by-the-user first implementation slice using
ONLY the approved requirements, architecture, and UI/UX design provided. These artifacts
are binding sources of truth. Do not add features or invent external services.
Choose a compact project structure and include meaningful implementation code, not
pseudocode, TODO-only stubs, or placeholder files. Include a README with setup and run
instructions and focused tests when the approved design supports them.
Return plain-text source files only; do not execute them, claim that they were run, or
claim they pass tests. Never include secrets, real credentials, production endpoints,
binary content, hidden files, environment files, or generated lockfiles.
Keep the bundle to at most 30 files and 200 KB total. Each file must be at most 30 KB.
Use relative POSIX paths with safe directory names. Allowed extensions: .py, .html,
.css, .js, .ts, .tsx, .jsx, .json, .md, .yaml, .yml, .toml.

Return exactly one JSON object, without Markdown fences, with keys:
implementation_summary, implementation_notes, files.
Each files item must contain path, language, purpose, content.
Do not add any other keys. Ensure paths are unique. Prefer a small end-to-end vertical
slice over a broad but incomplete code dump. Treat every generated file as untrusted text.
"""


class CodeGenerator:
    """Generate a bounded source bundle; never executes generated content."""

    name = "Code Generator"
    max_attempts = 2

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    @staticmethod
    def _parse_response(raw: str) -> CodeGenerationDocument:
        cleaned = raw.strip()
        match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.IGNORECASE | re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
        return CodeGenerationDocument.model_validate_json(cleaned)

    def run(self, context: AgentContext) -> AgentResult:
        requirements = context.prior_artifacts.get("requirements")
        architecture = context.prior_artifacts.get("architecture")
        uiux_design = context.prior_artifacts.get("uiux_design")
        if not all(isinstance(item, dict) for item in (requirements, architecture, uiux_design)):
            raise AgentExecutionError(
                "Approved requirements, architecture, and UI/UX design are required before code generation."
            )

        user_prompt = (
            "APPROVED REQUIREMENTS:\n" + json.dumps(requirements, ensure_ascii=False, indent=2)
            + "\n\nAPPROVED ARCHITECTURE:\n" + json.dumps(architecture, ensure_ascii=False, indent=2)
            + "\n\nAPPROVED UI/UX DESIGN:\n" + json.dumps(uiux_design, ensure_ascii=False, indent=2)
            + "\n\nPROJECT CONSTRAINTS:\n"
            + ("\n".join(f"- {item}" for item in context.constraints) or "- None supplied")
            + "\n\nGenerate a compact, coherent first implementation slice as a validated source bundle."
        )
        correction = ""
        last_error = ""
        for _attempt in range(1, self.max_attempts + 1):
            prompt = user_prompt
            if correction:
                prompt += (
                    "\n\nYour previous response failed the source bundle contract. "
                    f"Correct the issue and return the complete JSON object only: {correction}"
                )
            raw = self.provider.generate(system_prompt=SYSTEM_PROMPT, user_prompt=prompt, temperature=0.1)
            try:
                document = self._parse_response(raw)
                return AgentResult(
                    agent_name=self.name,
                    status="needs_review",
                    summary=(
                        f"Generated {len(document.files)} source files "
                        f"({sum(len(item.content.encode('utf-8')) for item in document.files):,} bytes). "
                        "Files are stored for review and have not been executed."
                    ),
                    artifact={"code_bundle": document.model_dump(mode="json")},
                    warnings=[
                        "Generated source is untrusted and has not been executed, tested, or security-reviewed.",
                        *document.implementation_notes,
                    ],
                )
            except (ValidationError, ValueError) as exc:
                last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                correction = last_error
        raise AgentExecutionError(
            f"Code Generator could not produce a valid source bundle after {self.max_attempts} attempts. "
            f"Last validation issue: {last_error}"
        )

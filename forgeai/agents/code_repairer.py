"""Bounded, evidence-led source repair specialist.

The agent proposes complete replacements for existing non-test source files only.
It never applies changes to the active project or executes generated code.
"""
from __future__ import annotations

import json
import re

from pydantic import ValidationError

from forgeai.agents.contracts import (
    AgentContext,
    AgentResult,
    CodeGenerationDocument,
    CodeRepairDocument,
)
from forgeai.providers.base import ModelProvider


class AgentExecutionError(RuntimeError):
    """Raised when a repair proposal cannot be validated."""


SYSTEM_PROMPT = """You are ForgeAI's senior software repair engineer.
Use only the supplied approved requirements, source files, failed test output, and
static review findings. Propose the smallest safe repair that addresses evidence-backed
issues. Return complete replacement content only for existing non-test source files.
Never edit, add, rename, or delete test files. Never add dependencies, shell scripts,
workflow files, Dockerfiles, credentials, environment files, or external services.
Do not claim the repair has been applied, executed, or verified. Do not change unrelated
behaviour. If evidence is insufficient, explain the uncertainty in unresolved_risks.
A maximum of 10 existing source files may be replaced; each replacement must be <=30 KB.
Use exact existing file paths. Do not output diffs; provide full replacement file content.

Return exactly one JSON object with keys:
repair_summary, changes, addressed_findings, unresolved_risks.
Each change: file_path, replacement_content, rationale, addresses.
No extra keys.
"""


class CodeRepairer:
    """Create a bounded repair candidate without modifying the active bundle."""

    name = "Code Repair Engineer"
    max_attempts = 2

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    def run(self, context: AgentContext) -> AgentResult:
        requirements = context.prior_artifacts.get("requirements")
        bundle = context.prior_artifacts.get("code_bundle")
        execution = context.prior_artifacts.get("execution_report", {})
        review = context.prior_artifacts.get("code_review", {})
        attempt = context.prior_artifacts.get("repair_attempt", 1)
        if not isinstance(requirements, dict) or not isinstance(bundle, dict):
            raise AgentExecutionError("Approved requirements and source bundle are required.")
        if attempt not in {1, 2}:
            raise AgentExecutionError("Only two repair proposals are permitted per repair cycle.")
        try:
            original = CodeGenerationDocument.model_validate(bundle)
        except (ValidationError, TypeError, ValueError) as exc:
            raise AgentExecutionError(f"Source bundle is invalid: {str(exc)[:400]}") from exc

        source_files = {
            item.path: item for item in original.files
            if not item.path.rsplit("/", 1)[-1].startswith("test_")
            and not item.path.endswith("_test.py")
        }
        if not source_files:
            raise AgentExecutionError("No eligible non-test source files are available to repair.")
        if not (
            isinstance(execution, dict) and execution.get("status") in
            {"failed", "timed_out", "output_limit_exceeded"}
        ) and not (isinstance(review, dict) and review.get("findings")):
            raise AgentExecutionError("A failed test execution or actionable static review finding is required.")

        prompt = (
            "APPROVED REQUIREMENTS:\n" + json.dumps(requirements, ensure_ascii=False, indent=2)
            + "\n\nCURRENT APPROVED SOURCE BUNDLE:\n" + json.dumps(bundle, ensure_ascii=False, indent=2)
            + "\n\nFAILED EXECUTION REPORT (may be empty):\n" + json.dumps(execution, ensure_ascii=False, indent=2)
            + "\n\nSTATIC REVIEW FINDINGS (may be empty):\n" + json.dumps(review, ensure_ascii=False, indent=2)
            + f"\n\nREPAIR ATTEMPT: {attempt} of 2. Propose only evidence-based source replacements."
        )
        correction = ""
        last_error = ""
        for _ in range(self.max_attempts):
            raw = self.provider.generate(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt + (f"\n\nCorrect this contract error: {correction}" if correction else ""),
                temperature=0.1,
            )
            try:
                cleaned = raw.strip()
                match = re.fullmatch(r"\x60\x60\x60(?:json)?\s*(.*?)\s*\x60\x60\x60", cleaned, re.I | re.S)
                if match:
                    cleaned = match.group(1).strip()
                proposal = CodeRepairDocument.model_validate_json(cleaned)
                changed = set()
                replacement_by_path = {}
                for change in proposal.changes:
                    if change.file_path not in source_files:
                        raise ValueError(f"Repair references a missing or protected file: {change.file_path}")
                    if change.file_path.rsplit("/", 1)[-1].startswith("test_") or change.file_path.endswith("_test.py"):
                        raise ValueError("Repair proposals cannot modify test files.")
                    changed.add(change.file_path)
                    replacement_by_path[change.file_path] = change.replacement_content
                repaired_files = [
                    item.model_copy(update={"content": replacement_by_path.get(item.path, item.content)})
                    for item in original.files
                ]
                candidate = CodeGenerationDocument(
                    implementation_summary=proposal.repair_summary,
                    implementation_notes=[
                        *original.implementation_notes,
                        f"Repair proposal attempt {attempt}; human approval and regression execution required.",
                    ],
                    files=repaired_files,
                )
                return AgentResult(
                    agent_name=self.name,
                    status="needs_review",
                    summary=f"Prepared a repair candidate changing {len(changed)} source file(s). It has not been applied or tested.",
                    artifact={
                        "repair_proposal": proposal.model_dump(mode="json"),
                        "code_bundle": candidate.model_dump(mode="json"),
                    },
                    warnings=[
                        "This is a proposed replacement bundle. Review it before approval; run regression tests afterward.",
                        "Test files were preserved unchanged. No code was executed by the repair agent.",
                    ],
                )
            except (ValidationError, ValueError) as exc:
                last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                correction = last_error
        raise AgentExecutionError(f"Repair proposal failed validation after {self.max_attempts} attempts: {last_error}")

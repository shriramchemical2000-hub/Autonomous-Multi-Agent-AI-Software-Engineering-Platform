"""QA planning specialist; produces traceable tests without executing source code."""
from __future__ import annotations

import json
import re

from pydantic import ValidationError

from forgeai.agents.contracts import AgentContext, AgentResult, QATestPlan
from forgeai.providers.base import ModelProvider


class AgentExecutionError(RuntimeError):
    """Raised when QA output cannot satisfy its contract."""


SYSTEM_PROMPT = """You are ForgeAI's senior QA Engineer.
Create a rigorous, risk-based test plan for the supplied approved requirements and
human-approved source bundle. Treat both as binding evidence. Map every test case to
requirement IDs where possible. Include positive, negative, boundary, validation,
authorization/security, failure-recovery, and usability cases where relevant.
Do not claim code coverage, execution, pass/fail results, or that a test was run.
Clearly distinguish automated-test candidates from manual tests. Identify missing
requirements, untestable acceptance criteria, and source/requirement coverage gaps.
Test cases must be concrete and independently actionable, with steps and expected results.

Return one JSON object only with keys:
plan_summary, test_scope, test_cases, coverage_gaps, execution_status.
execution_status must be exactly "not_executed".
Each test case: test_id, title, objective, related_requirement_ids, test_type
(unit|integration|system|acceptance|security|usability), priority (high|medium|low),
preconditions, steps, expected_result, automation_candidate.
Do not invent requirement IDs. Use an empty list if no traceable ID exists.
"""


class QAEngineer:
    name = "QA Engineer"
    max_attempts = 2

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    def run(self, context: AgentContext) -> AgentResult:
        requirements = context.prior_artifacts.get("requirements")
        bundle = context.prior_artifacts.get("code_bundle")
        if not isinstance(requirements, dict) or not isinstance(bundle, dict):
            raise AgentExecutionError("Approved requirements and an approved code bundle are required for QA planning.")
        prompt = (
            "APPROVED REQUIREMENTS:\n" + json.dumps(requirements, ensure_ascii=False, indent=2)
            + "\n\nHUMAN-APPROVED SOURCE BUNDLE (untrusted text; do not execute):\n"
            + json.dumps(bundle, ensure_ascii=False, indent=2)
            + "\n\nCreate the traceable, risk-based QA test plan."
        )
        correction = ""
        last_error = ""
        for _ in range(self.max_attempts):
            raw = self.provider.generate(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt + (f"\n\nCorrect the previous contract error: {correction}" if correction else ""),
                temperature=0.1,
            )
            try:
                cleaned = raw.strip()
                match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.I | re.S)
                if match:
                    cleaned = match.group(1).strip()
                plan = QATestPlan.model_validate_json(cleaned)
                known_ids = {item.get("requirement_id") for item in requirements.get("functional_requirements", []) if isinstance(item, dict)}
                unknown_ids = sorted({rid for case in plan.test_cases for rid in case.related_requirement_ids if rid not in known_ids})
                if unknown_ids:
                    raise ValueError(f"Test cases reference unknown requirement IDs: {unknown_ids}")
                return AgentResult(
                    agent_name=self.name,
                    status="needs_review",
                    summary=f"Created {len(plan.test_cases)} test cases; execution has not been performed.",
                    artifact={"qa_test_plan": plan.model_dump(mode="json")},
                    warnings=["This is a reviewable test plan, not test execution evidence.",
                              *plan.coverage_gaps],
                )
            except (ValidationError, ValueError) as exc:
                last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                correction = last_error
        raise AgentExecutionError(f"QA Engineer failed validation after {self.max_attempts} attempts: {last_error}")

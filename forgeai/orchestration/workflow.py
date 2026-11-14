"""LangGraph orchestration for ForgeAI's approval-gated specialist workflow."""
from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from forgeai.agents.contracts import AgentContext
from forgeai.agents.requirements_analyst import RequirementsAnalyst
from forgeai.agents.software_architect import SoftwareArchitect
from forgeai.agents.uiux_designer import UIUXDesigner
from forgeai.agents.code_generator import CodeGenerator
from forgeai.agents.qa_engineer import QAEngineer
from forgeai.agents.code_reviewer import CodeReviewer
from forgeai.agents.code_repairer import CodeRepairer
from forgeai.orchestration.state import ForgeWorkflowState
from forgeai.providers.base import ModelProvider


def _route_entry(state: ForgeWorkflowState) -> Literal["requirements", "architecture", "uiux", "codegen", "qa", "review", "repair"]:
    requested = state.get("requested_stage")
    if requested not in {"requirements", "architecture", "uiux", "codegen", "qa", "review", "repair"}:
        raise ValueError("requested_stage must be one of requirements, architecture, uiux, codegen, qa, review, or repair.")
    return requested  # type: ignore[return-value]


def _requirements_node(provider: ModelProvider):
    def run(state: ForgeWorkflowState) -> ForgeWorkflowState:
        result = RequirementsAnalyst(provider).run(
            AgentContext(
                project_id=state["project_id"],
                user_request=state["user_request"],
                constraints=state.get("constraints", []),
            )
        )
        return {
            "requirements": result.artifact["requirements"],
            "current_stage": "requirements_review",
            "status": "awaiting_human_approval",
            "summary": result.summary,
            "warnings": result.warnings,
            "messages": [{"agent": result.agent_name, "status": result.status, "summary": result.summary}],
        }
    return run


def _architecture_node(provider: ModelProvider):
    def run(state: ForgeWorkflowState) -> ForgeWorkflowState:
        if state.get("requirements_approved") is not True:
            raise ValueError("Architecture is blocked: the latest requirements must be explicitly approved.")
        requirements = state.get("requirements")
        if not isinstance(requirements, dict):
            raise ValueError("Architecture requires the approved requirements artifact.")
        result = SoftwareArchitect(provider).run(
            AgentContext(
                project_id=state["project_id"],
                user_request=f"Design the approved product: {requirements.get('product_name', 'Unnamed product')}.",
                constraints=state.get("constraints", []),
                prior_artifacts={"requirements": requirements},
            )
        )
        return {
            "architecture": result.artifact["architecture"],
            "current_stage": "architecture_review",
            "status": "awaiting_human_approval",
            "summary": result.summary,
            "warnings": result.warnings,
            "messages": [{"agent": result.agent_name, "status": result.status, "summary": result.summary}],
        }
    return run


def _uiux_node(provider: ModelProvider):
    def run(state: ForgeWorkflowState) -> ForgeWorkflowState:
        if state.get("requirements_approved") is not True:
            raise ValueError("UI/UX design is blocked: requirements must be explicitly approved.")
        if state.get("architecture_approved") is not True:
            raise ValueError("UI/UX design is blocked: architecture must be explicitly approved.")
        requirements = state.get("requirements")
        architecture = state.get("architecture")
        if not isinstance(requirements, dict) or not isinstance(architecture, dict):
            raise ValueError("UI/UX design requires both approved requirements and architecture artifacts.")
        result = UIUXDesigner(provider).run(
            AgentContext(
                project_id=state["project_id"],
                user_request=f"Design the user experience for {requirements.get('product_name', 'the product')}.",
                constraints=state.get("constraints", []),
                prior_artifacts={"requirements": requirements, "architecture": architecture},
            )
        )
        return {
            "uiux_design": result.artifact["uiux_design"],
            "current_stage": "uiux_review",
            "status": "awaiting_human_approval",
            "summary": result.summary,
            "warnings": result.warnings,
            "messages": [{"agent": result.agent_name, "status": result.status, "summary": result.summary}],
        }
    return run


def _codegen_node(provider: ModelProvider):
    def run(state: ForgeWorkflowState) -> ForgeWorkflowState:
        if state.get("requirements_approved") is not True:
            raise ValueError("Code generation is blocked: requirements must be explicitly approved.")
        if state.get("architecture_approved") is not True:
            raise ValueError("Code generation is blocked: architecture must be explicitly approved.")
        if state.get("uiux_approved") is not True:
            raise ValueError("Code generation is blocked: UI/UX design must be explicitly approved.")
        requirements = state.get("requirements")
        architecture = state.get("architecture")
        uiux_design = state.get("uiux_design")
        if not all(isinstance(item, dict) for item in (requirements, architecture, uiux_design)):
            raise ValueError("Code generation requires approved requirements, architecture, and UI/UX artifacts.")
        result = CodeGenerator(provider).run(
            AgentContext(
                project_id=state["project_id"],
                user_request=f"Implement the approved product: {requirements.get('product_name', 'the product')}.",
                constraints=state.get("constraints", []),
                prior_artifacts={
                    "requirements": requirements,
                    "architecture": architecture,
                    "uiux_design": uiux_design,
                },
            )
        )
        return {
            "code_bundle": result.artifact["code_bundle"],
            "current_stage": "code_review",
            "status": "awaiting_human_approval",
            "summary": result.summary,
            "warnings": result.warnings,
            "messages": [{"agent": result.agent_name, "status": result.status, "summary": result.summary}],
        }
    return run




def _qa_node(provider: ModelProvider):
    def run(state: ForgeWorkflowState) -> ForgeWorkflowState:
        if state.get("requirements_approved") is not True:
            raise ValueError("QA planning requires approved requirements.")
        if state.get("code_bundle_approved") is not True:
            raise ValueError("QA planning requires an approved source bundle.")
        requirements, bundle = state.get("requirements"), state.get("code_bundle")
        if not isinstance(requirements, dict) or not isinstance(bundle, dict):
            raise ValueError("QA planning requires requirements and source bundle artifacts.")
        result = QAEngineer(provider).run(AgentContext(
            project_id=state["project_id"], user_request="Create a risk-based test plan.",
            constraints=state.get("constraints", []),
            prior_artifacts={"requirements": requirements, "code_bundle": bundle},
        ))
        return {"qa_test_plan": result.artifact["qa_test_plan"], "current_stage": "qa_review",
                "status": "awaiting_human_approval", "summary": result.summary,
                "warnings": result.warnings,
                "messages": [{"agent": result.agent_name, "status": result.status, "summary": result.summary}]}
    return run


def _review_node(provider: ModelProvider):
    def run(state: ForgeWorkflowState) -> ForgeWorkflowState:
        if state.get("requirements_approved") is not True:
            raise ValueError("Code review requires approved requirements.")
        if state.get("code_bundle_approved") is not True:
            raise ValueError("Code review requires an approved source bundle.")
        requirements, bundle = state.get("requirements"), state.get("code_bundle")
        architecture = state.get("architecture", {})
        if not isinstance(requirements, dict) or not isinstance(bundle, dict):
            raise ValueError("Code review requires requirements and source bundle artifacts.")
        result = CodeReviewer(provider).run(AgentContext(
            project_id=state["project_id"], user_request="Perform a static source review.",
            constraints=state.get("constraints", []),
            prior_artifacts={"requirements": requirements, "architecture": architecture, "code_bundle": bundle},
        ))
        return {"code_review": result.artifact["code_review"], "current_stage": "code_review_complete",
                "status": "awaiting_human_approval", "summary": result.summary,
                "warnings": result.warnings,
                "messages": [{"agent": result.agent_name, "status": result.status, "summary": result.summary}]}
    return run



def _repair_node(provider: ModelProvider):
    def run(state: ForgeWorkflowState) -> ForgeWorkflowState:
        if state.get("requirements_approved") is not True:
            raise ValueError("Code repair requires approved requirements.")
        if state.get("code_bundle_approved") is not True:
            raise ValueError("Code repair requires an approved source bundle.")
        if state.get("repair_authorized") is not True:
            raise ValueError("Code repair requires explicit operator authorization.")
        attempt = state.get("repair_attempt")
        if attempt not in {1, 2}:
            raise ValueError("Code repair is limited to two proposals per repair cycle.")
        requirements = state.get("requirements")
        bundle = state.get("code_bundle")
        execution_report = state.get("execution_report", {})
        code_review = state.get("code_review", {})
        if not isinstance(requirements, dict) or not isinstance(bundle, dict):
            raise ValueError("Code repair requires approved requirements and a source bundle.")
        execution_failed = isinstance(execution_report, dict) and execution_report.get("status") in {
            "failed", "timed_out", "output_limit_exceeded"
        }
        review_findings = code_review.get("findings", []) if isinstance(code_review, dict) else []
        if not execution_failed and not review_findings:
            raise ValueError("Code repair requires a failed execution report or actionable review findings.")
        result = CodeRepairer(provider).run(AgentContext(
            project_id=state["project_id"],
            user_request="Propose a narrowly scoped repair for the supplied verified failures/findings.",
            constraints=state.get("constraints", []),
            prior_artifacts={
                "requirements": requirements,
                "code_bundle": bundle,
                "execution_report": execution_report,
                "code_review": code_review,
                "repair_attempt": attempt,
            },
        ))
        return {
            "code_bundle": result.artifact["code_bundle"],
            "repair_proposal": result.artifact["repair_proposal"],
            "current_stage": "repair_review",
            "status": "awaiting_human_approval",
            "summary": result.summary,
            "warnings": result.warnings,
            "messages": [{"agent": result.agent_name, "status": result.status, "summary": result.summary}],
        }
    return run


def build_forge_workflow(provider: ModelProvider):
    """Compile the bounded graph; each invocation executes one stage and ends for review."""
    graph = StateGraph(ForgeWorkflowState)
    graph.add_node("requirements_analyst", _requirements_node(provider))
    graph.add_node("software_architect", _architecture_node(provider))
    graph.add_node("uiux_designer", _uiux_node(provider))
    graph.add_node("code_generator", _codegen_node(provider))
    graph.add_node("qa_engineer", _qa_node(provider))
    graph.add_node("code_reviewer", _review_node(provider))
    graph.add_node("code_repairer", _repair_node(provider))
    graph.add_conditional_edges(
        START,
        _route_entry,
        {
            "requirements": "requirements_analyst",
            "architecture": "software_architect",
            "uiux": "uiux_designer",
            "codegen": "code_generator",
            "qa": "qa_engineer",
            "review": "code_reviewer",
            "repair": "code_repairer",
        },
    )
    graph.add_edge("requirements_analyst", END)
    graph.add_edge("software_architect", END)
    graph.add_edge("uiux_designer", END)
    graph.add_edge("code_generator", END)
    graph.add_edge("qa_engineer", END)
    graph.add_edge("code_reviewer", END)
    graph.add_edge("code_repairer", END)
    return graph.compile()

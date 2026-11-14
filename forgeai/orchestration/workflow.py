"""LangGraph orchestration for ForgeAI's approval-gated specialist workflow.

Each invocation executes one bounded stage. SQLite remains the durable source of
project/artifact history; the caller supplies the latest approved artifact when
starting the next stage. The graph itself does not pretend to persist checkpoints.
"""
from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from forgeai.agents.contracts import AgentContext
from forgeai.agents.requirements_analyst import RequirementsAnalyst
from forgeai.agents.software_architect import SoftwareArchitect
from forgeai.orchestration.state import ForgeWorkflowState
from forgeai.providers.base import ModelProvider


def _route_entry(state: ForgeWorkflowState) -> Literal["requirements", "architecture"]:
    requested = state.get("requested_stage")
    if requested not in {"requirements", "architecture"}:
        raise ValueError("requested_stage must be 'requirements' or 'architecture'.")
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
            "messages": [{
                "agent": result.agent_name,
                "status": result.status,
                "summary": result.summary,
            }],
        }
    return run


def _architecture_node(provider: ModelProvider):
    def run(state: ForgeWorkflowState) -> ForgeWorkflowState:
        if state.get("requirements_approved") is not True:
            raise ValueError(
                "Architecture is blocked: the latest requirements must be explicitly approved."
            )
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
            "messages": [{
                "agent": result.agent_name,
                "status": result.status,
                "summary": result.summary,
            }],
        }
    return run


def build_forge_workflow(provider: ModelProvider):
    """Compile the bounded, approval-gated specialist graph."""
    graph = StateGraph(ForgeWorkflowState)
    graph.add_node("requirements_analyst", _requirements_node(provider))
    graph.add_node("software_architect", _architecture_node(provider))
    graph.add_conditional_edges(
        START,
        _route_entry,
        {
            "requirements": "requirements_analyst",
            "architecture": "software_architect",
        },
    )
    graph.add_edge("requirements_analyst", END)
    graph.add_edge("software_architect", END)
    return graph.compile()

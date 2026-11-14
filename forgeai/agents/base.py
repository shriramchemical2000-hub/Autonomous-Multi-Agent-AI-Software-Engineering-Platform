"""Common protocol for executable specialist agents."""
from __future__ import annotations

from typing import Protocol

from forgeai.agents.contracts import AgentContext, AgentResult


class SpecialistAgent(Protocol):
    """A specialist consumes a typed context and returns a typed result."""

    name: str

    def run(self, context: AgentContext) -> AgentResult:
        """Execute one bounded unit of specialist work."""
        ...

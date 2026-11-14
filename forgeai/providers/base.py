"""Provider interface independent of any specific model vendor."""
from __future__ import annotations

from typing import Protocol


class ModelProviderError(RuntimeError):
    """Raised when a model provider cannot complete a request."""


class ModelProvider(Protocol):
    """Minimal text-generation contract consumed by agent services."""

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """Return generated text or raise ModelProviderError."""
        ...

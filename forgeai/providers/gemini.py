"""Gemini adapter implemented through LangChain's chat-model interface."""
from __future__ import annotations

from forgeai.config import Settings, get_settings
from forgeai.providers.base import ModelProviderError


class GeminiProvider:
    """Lazy Gemini client; importing ForgeAI does not require an API key."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        if not self.settings.has_model_api_key:
            raise ModelProviderError(
                "GEMINI_API_KEY is not configured. Add it to your environment before calling the model."
            )
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")

        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_google_genai import ChatGoogleGenerativeAI

            model = ChatGoogleGenerativeAI(
                model=self.settings.model_name,
                google_api_key=self.settings.gemini_api_key,
                temperature=temperature,
            )
            response = model.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            content = response.content
            if isinstance(content, str):
                text = content.strip()
            elif isinstance(content, list):
                text = "\n".join(
                    str(part.get("text", "")) if isinstance(part, dict) else str(part)
                    for part in content
                ).strip()
            else:
                text = str(content).strip()
            if not text:
                raise ModelProviderError("The model returned an empty response.")
            return text
        except ModelProviderError:
            raise
        except Exception as exc:
            # Avoid exposing request payloads or credentials in user-facing errors.
            raise ModelProviderError(
                f"Gemini request failed ({type(exc).__name__}). Check model availability and configuration."
            ) from exc

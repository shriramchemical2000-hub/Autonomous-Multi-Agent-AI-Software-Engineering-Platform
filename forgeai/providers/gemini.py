"""Gemini adapter implemented through LangChain's chat-model interface."""
from __future__ import annotations

from forgeai.config import Settings, get_settings
from forgeai.providers.base import ModelProviderError


class GeminiProvider:
    """Lazy Gemini client with bounded fallback for temporary Google outages."""

    FALLBACK_MODELS = ("gemini-3.7-flash", "gemini-3.6-flash")

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @staticmethod
    def _is_transient_provider_error(exc: Exception) -> bool:
        """Only fail over for temporary availability/deadline failures."""
        status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        detail = f"{type(exc).__name__} {exc}".upper()
        return (
            status_code in (503, 504)
            or "503" in detail
            or "UNAVAILABLE" in detail
            or "504" in detail
            or "DEADLINE_EXCEEDED" in detail
        )

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

            candidates = tuple(dict.fromkeys(
                (self.settings.model_name, *self.FALLBACK_MODELS)
            ))
            attempted: list[str] = []
            last_error: Exception | None = None

            for model_name in candidates:
                attempted.append(model_name)
                try:
                    model = ChatGoogleGenerativeAI(
                        model=model_name,
                        google_api_key=self.settings.gemini_api_key,
                        temperature=temperature,
                        timeout=90,
                        max_retries=0,
                        max_output_tokens=8192,
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
                    last_error = exc
                    # Do not mask invalid keys, permissions, missing models, or quota errors
                    # by repeatedly trying other model names.
                    if not self._is_transient_provider_error(exc):
                        raise
                    continue

            assert last_error is not None
            detail = str(last_error).replace(self.settings.gemini_api_key, "[REDACTED]")
            detail = " ".join(detail.split())[:500]
            raise ModelProviderError(
                "All configured Gemini models are temporarily unavailable "
                f"({', '.join(attempted)}). Last error: "
                f"{type(last_error).__name__}: {detail or 'No provider details returned.'} "
                "Please retry later."
            ) from last_error
        except ModelProviderError:
            raise
        except Exception as exc:
            # Avoid exposing request payloads or credentials in user-facing errors.
            detail = str(exc).replace(self.settings.gemini_api_key, "[REDACTED]")
            detail = " ".join(detail.split())[:700]
            raise ModelProviderError(
                f"Gemini request failed ({type(exc).__name__}): {detail or 'No provider details returned.'}"
            ) from exc

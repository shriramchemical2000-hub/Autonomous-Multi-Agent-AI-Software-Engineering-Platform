"""NVIDIA NIM adapter using its OpenAI-compatible hosted API."""
from __future__ import annotations

from forgeai.config import Settings, get_settings
from forgeai.providers.base import ModelProviderError


class NvidiaProvider:
    """Lazy NVIDIA NIM client; agents remain vendor-independent."""

    BASE_URL = "https://integrate.api.nvidia.com/v1"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        if not self.settings.has_nvidia_api_key:
            raise ModelProviderError(
                "NVIDIA_API_KEY is not configured. Add it to Streamlit Secrets or the environment."
            )
        if not 0.0 <= temperature <= 1.0:
            raise ValueError("temperature must be between 0.0 and 1.0 for NVIDIA NIM.")

        try:
            from openai import OpenAI

            client = OpenAI(
                base_url=self.BASE_URL,
                api_key=self.settings.nvidia_api_key,
                timeout=120.0,
                max_retries=1,
            )
            response = client.chat.completions.create(
                model=self.settings.nvidia_model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                # Nemotron 3.5 is a reasoning model. Disable hidden reasoning for
                # structured agent outputs so the token budget is spent on the
                # JSON/text that ForgeAI must validate and save.
                max_tokens=16384,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            choices = getattr(response, "choices", None) or []
            if not choices:
                raise ModelProviderError(
                    "NVIDIA returned no completion choices. Check model availability and retry."
                )
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None)
            if isinstance(content, str) and content.strip():
                return content.strip()

            finish_reason = getattr(choices[0], "finish_reason", None) or "unknown"
            raise ModelProviderError(
                "NVIDIA returned no visible text "
                f"(finish_reason={finish_reason}). The model may have used its output "
                "budget for reasoning; ForgeAI now requests visible output with reasoning disabled."
            )
        except ModelProviderError:
            raise
        except Exception as exc:
            detail = str(exc).replace(self.settings.nvidia_api_key, "[REDACTED]")
            detail = " ".join(detail.split())[:700]
            raise ModelProviderError(
                f"NVIDIA NIM request failed ({type(exc).__name__}): "
                f"{detail or 'No provider details returned.'}"
            ) from exc

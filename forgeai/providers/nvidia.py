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
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")

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
                max_tokens=8192,
            )
            content = response.choices[0].message.content
            if not isinstance(content, str) or not content.strip():
                raise ModelProviderError("NVIDIA returned an empty response.")
            return content.strip()
        except ModelProviderError:
            raise
        except Exception as exc:
            detail = str(exc).replace(self.settings.nvidia_api_key, "[REDACTED]")
            detail = " ".join(detail.split())[:700]
            raise ModelProviderError(
                f"NVIDIA NIM request failed ({type(exc).__name__}): "
                f"{detail or 'No provider details returned.'}"
            ) from exc

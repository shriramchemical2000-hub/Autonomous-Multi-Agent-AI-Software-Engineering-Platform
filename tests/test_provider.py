import pytest

from forgeai.config import Settings
from forgeai.providers.base import ModelProviderError
from forgeai.providers.gemini import GeminiProvider


def test_gemini_provider_requires_key_before_network_call(tmp_path):
    settings = Settings(
        environment="test",
        database_path=tmp_path / "test.db",
        gemini_api_key="",
        model_name="gemini-2.5-flash",
    )
    provider = GeminiProvider(settings)
    with pytest.raises(ModelProviderError, match="GEMINI_API_KEY"):
        provider.generate(system_prompt="system", user_prompt="hello")


def test_gemini_provider_rejects_invalid_temperature(tmp_path):
    settings = Settings(
        environment="test",
        database_path=tmp_path / "test.db",
        gemini_api_key="test-key",
        model_name="gemini-2.5-flash",
    )
    provider = GeminiProvider(settings)
    with pytest.raises(ValueError, match="temperature"):
        provider.generate(system_prompt="system", user_prompt="hello", temperature=2.5)

import pytest

from forgeai.config import Settings
from forgeai.providers.base import ModelProviderError
from forgeai.providers.gemini import GeminiProvider


def _settings(tmp_path):
    return Settings(
        environment="test",
        database_path=tmp_path / "test.db",
        gemini_api_key="test-key",
        model_name="gemini-3.8-flash",
    )


def test_gemini_provider_requires_key_before_network_call(tmp_path):
    settings = Settings(
        environment="test",
        database_path=tmp_path / "test.db",
        gemini_api_key="",
        model_name="gemini-3.8-flash",
    )
    provider = GeminiProvider(settings)
    with pytest.raises(ModelProviderError, match="GEMINI_API_KEY"):
        provider.generate(system_prompt="system", user_prompt="hello")


def test_gemini_provider_rejects_invalid_temperature(tmp_path):
    provider = GeminiProvider(_settings(tmp_path))
    with pytest.raises(ValueError, match="temperature"):
        provider.generate(system_prompt="system", user_prompt="hello", temperature=2.5)


def test_gemini_provider_falls_back_after_temporary_unavailability(tmp_path, monkeypatch):
    import langchain_google_genai

    calls = []

    class FakeModel:
        def __init__(self, *, model, **kwargs):
            self.model = model
            calls.append(model)

        def invoke(self, messages):
            if self.model == "gemini-3.8-flash":
                raise RuntimeError("503 UNAVAILABLE: temporary overload")

            class Response:
                content = "  generated successfully  "

            return Response()

    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", FakeModel)
    provider = GeminiProvider(_settings(tmp_path))

    result = provider.generate(system_prompt="system", user_prompt="hello")

    assert result == "generated successfully"
    assert calls == ["gemini-3.8-flash", "gemini-3.7-flash"]


def test_gemini_provider_does_not_fallback_for_authentication_errors(tmp_path, monkeypatch):
    import langchain_google_genai

    calls = []

    class FakeModel:
        def __init__(self, *, model, **kwargs):
            calls.append(model)

        def invoke(self, messages):
            raise RuntimeError("403 PERMISSION_DENIED: invalid API key")

    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", FakeModel)
    provider = GeminiProvider(_settings(tmp_path))

    with pytest.raises(ModelProviderError, match="403 PERMISSION_DENIED"):
        provider.generate(system_prompt="system", user_prompt="hello")

    assert calls == ["gemini-3.8-flash"]

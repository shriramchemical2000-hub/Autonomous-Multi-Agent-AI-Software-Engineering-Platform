from types import SimpleNamespace

import pytest

from forgeai.config import Settings
from forgeai.providers.base import ModelProviderError
from forgeai.providers.nvidia import NvidiaProvider


def _settings(tmp_path, *, key="test-nvidia-key", model="nvidia/nemotron-3.5-lightning-30b-a3b"):
    return Settings(
        environment="test",
        database_path=tmp_path / "test.db",
        gemini_api_key="",
        model_name="gemini-3.8-flash",
        nvidia_api_key=key,
        nvidia_model_name=model,
    )


def test_nvidia_provider_requires_key(tmp_path):
    provider = NvidiaProvider(_settings(tmp_path, key=""))
    with pytest.raises(ModelProviderError, match="NVIDIA_API_KEY"):
        provider.generate(system_prompt="system", user_prompt="hello")


def test_nvidia_provider_rejects_invalid_temperature(tmp_path):
    provider = NvidiaProvider(_settings(tmp_path))
    with pytest.raises(ValueError, match="temperature"):
        provider.generate(system_prompt="system", user_prompt="hello", temperature=2.1)


def test_nvidia_provider_uses_nim_and_returns_text(tmp_path, monkeypatch):
    import sys

    calls = {}

    class FakeCompletions:
        def create(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="  architecture ready  "))]
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            calls["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    provider = NvidiaProvider(_settings(tmp_path))

    result = provider.generate(system_prompt="system prompt", user_prompt="user prompt", temperature=0.1)

    assert result == "architecture ready"
    assert calls["client"]["base_url"] == "https://integrate.api.nvidia.com/v1"
    assert calls["client"]["api_key"] == "test-nvidia-key"
    assert calls["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert calls["max_tokens"] == 16384
    assert calls["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert calls["messages"][0] == {"role": "system", "content": "system prompt"}
    assert calls["messages"][1] == {"role": "user", "content": "user prompt"}


def test_nvidia_provider_redacts_api_key_from_errors(tmp_path, monkeypatch):
    import sys

    class FakeCompletions:
        def create(self, **kwargs):
            raise RuntimeError("request failed with test-nvidia-key")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    provider = NvidiaProvider(_settings(tmp_path))

    with pytest.raises(ModelProviderError) as error:
        provider.generate(system_prompt="system", user_prompt="hello")

    assert "test-nvidia-key" not in str(error.value)
    assert "[REDACTED]" in str(error.value)

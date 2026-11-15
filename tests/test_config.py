from forgeai.config import get_settings


def test_settings_have_safe_defaults(monkeypatch):
    for key in ("FORGEAI_ENV", "FORGEAI_DB_PATH", "GEMINI_API_KEY", "FORGEAI_MODEL", "NVIDIA_API_KEY", "NVIDIA_MODEL"):
        monkeypatch.delenv(key, raising=False)
    settings = get_settings()
    assert settings.environment == "development"
    assert str(settings.database_path) == "data/forgeai.db"
    assert settings.gemini_api_key == ""
    assert settings.has_model_api_key is False
    assert settings.model_name == "gemini-3.8-flash"
    assert settings.nvidia_api_key == ""
    assert settings.has_nvidia_api_key is False
    assert settings.nvidia_model_name == "nvidia/nemotron-3.5-lightning-30b-a3b"

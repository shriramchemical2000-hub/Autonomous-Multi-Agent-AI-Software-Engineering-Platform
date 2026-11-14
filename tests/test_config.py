from forgeai.config import get_settings


def test_settings_have_safe_defaults(monkeypatch):
    for key in ("FORGEAI_ENV", "FORGEAI_DB_PATH", "GEMINI_API_KEY", "FORGEAI_MODEL"):
        monkeypatch.delenv(key, raising=False)
    settings = get_settings()
    assert settings.environment == "development"
    assert str(settings.database_path) == "data/forgeai.db"
    assert settings.gemini_api_key == ""
    assert settings.has_model_api_key is False
    assert settings.model_name

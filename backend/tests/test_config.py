import pytest

from app.config.settings import VALID_ENVIRONMENTS, ConfigurationError, Settings


class TestSettingsFromEnv:
    def test_default_values(self):
        settings = Settings.from_env()
        assert settings.environment == "development"
        assert settings.database_url == "sqlite:///./ipp.db"
        assert settings.model_storage_path == "./models"

    def test_uses_env_vars(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "testing")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-key")
        settings = Settings.from_env()
        assert settings.environment == "testing"
        assert settings.database_url == "sqlite:///./test.db"
        assert settings.jwt_secret_key == "test-key"

    def test_invalid_environment_raises(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "staging")
        with pytest.raises(ConfigurationError, match="Invalid APP_ENV"):
            Settings.from_env()

    def test_production_requires_non_default_secret(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("JWT_SECRET_KEY", "development-only-change-me")
        with pytest.raises(ConfigurationError, match="JWT_SECRET_KEY must be changed"):
            Settings.from_env()

    def test_production_with_custom_secret(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("JWT_SECRET_KEY", "my-production-secret-key")
        settings = Settings.from_env()
        assert settings.environment == "production"
        assert settings.jwt_secret_key == "my-production-secret-key"

    def test_env_file_loading(self, monkeypatch, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("APP_ENV=testing\nJWT_SECRET_KEY=from-file-key\n")
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        settings = Settings.from_env(env_file)
        assert settings.environment == "testing"
        assert settings.jwt_secret_key == "from-file-key"


class TestValidEnvironments:
    def test_contains_expected(self):
        assert "development" in VALID_ENVIRONMENTS
        assert "testing" in VALID_ENVIRONMENTS
        assert "production" in VALID_ENVIRONMENTS
        assert len(VALID_ENVIRONMENTS) == 3


class TestSettingsFrozen:
    def test_is_frozen(self):
        settings = Settings.from_env()
        with pytest.raises((AttributeError, Exception)):
            settings.environment = "production"  # type: ignore

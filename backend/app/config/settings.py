from dataclasses import dataclass
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

VALID_ENVIRONMENTS = frozenset({"development", "testing", "production"})


class ConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    jwt_secret_key: str
    jwt_access_token_minutes: int
    jwt_refresh_token_days: int
    admin_email: str | None
    admin_password: str | None
    model_storage_path: str

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "Settings":
        if env_file is not None:
            load_dotenv(env_file, override=False)
        else:
            load_dotenv(override=False)
        environment = getenv("APP_ENV", "development")
        if environment not in VALID_ENVIRONMENTS:
            raise ConfigurationError(
                f"Invalid APP_ENV '{environment}'. Must be one of {sorted(VALID_ENVIRONMENTS)}."
            )
        jwt_secret_key = getenv("JWT_SECRET_KEY", "development-only-change-me")
        if environment == "production" and jwt_secret_key == "development-only-change-me":
            raise ConfigurationError("JWT_SECRET_KEY must be changed in production.")
        admin_email = getenv("ADMIN_EMAIL")
        admin_password = getenv("ADMIN_PASSWORD")
        return cls(
            environment=environment,
            database_url=getenv("DATABASE_URL", "sqlite:///./ipp.db"),
            jwt_secret_key=jwt_secret_key,
            jwt_access_token_minutes=int(getenv("JWT_ACCESS_TOKEN_MINUTES", "30")),
            jwt_refresh_token_days=int(getenv("JWT_REFRESH_TOKEN_DAYS", "7")),
            admin_email=admin_email,
            admin_password=admin_password,
            model_storage_path=getenv("MODEL_STORAGE_PATH", "./models"),
        )

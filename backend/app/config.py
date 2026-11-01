from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./finora.db"
    staff_username: str
    staff_password: str
    jwt_secret: str
    jwt_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173"
    faq_path: str = str(Path(__file__).resolve().parents[2] / "data" / "faq.json")
    chat_rate_limit: int = 30
    chat_rate_window_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("staff_password")
    @classmethod
    def validate_staff_password(cls, value: str) -> str:
        normalized = value.casefold()
        if len(value) < 12:
            raise ValueError("STAFF_PASSWORD must contain at least 12 characters")
        if any(placeholder in normalized for placeholder in ("replace-with", "change-me", "your-local")):
            raise ValueError("STAFF_PASSWORD must not use a placeholder value")
        return value

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        normalized = value.casefold()
        if len(value) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        if any(placeholder in normalized for placeholder in ("replace-with", "change-this", "your-local")):
            raise ValueError("JWT_SECRET must not use a placeholder value")
        return value


settings = Settings()

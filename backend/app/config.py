from typing import Optional
from urllib.parse import urlparse
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SMC Academy Referral API"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./smc_referral.db"

    # Telegram Bot
    BOT_TOKEN: str = ""

    # Webhook security
    WEBHOOK_SECRET: str = Field(min_length=32)

    # Google Form Configuration
    # Full viewform URL with usp=pp_url so pre-fill query params work correctly
    GOOGLE_FORM_BASE_URL: str = "https://docs.google.com/forms/d/e/1FAIpQLSfECyZnd6SXkMCwouJH5AnBU_ehiDDjHizGgkZV_qhs5Ker8A/viewform"
    # Confirmed referral field entry ID from the SMC Academy Google Form
    GOOGLE_FORM_REFERRAL_ENTRY_ID: Optional[str] = "entry.1398965380"


    # Frontend Mini App URL
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"
    TELEGRAM_MINI_APP_BASE_URL: str = "https://t.me/SMCARtrackerbot"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    def validate_production(self) -> None:
        """Reject unsafe or incomplete settings before starting production."""
        if self.ENVIRONMENT.lower() != "production":
            return

        errors: list[str] = []
        if not self.BOT_TOKEN.strip():
            errors.append("BOT_TOKEN must be set")
        if len(self.SECRET_KEY) < 32:
            errors.append("SECRET_KEY must be at least 32 characters")
        if len(self.WEBHOOK_SECRET) < 32:
            errors.append("WEBHOOK_SECRET must be at least 32 characters")
        if self.DATABASE_URL.lower().startswith("sqlite"):
            errors.append("DATABASE_URL must use a production database, not SQLite")

        for name, value in (
            ("FRONTEND_URL", self.FRONTEND_URL),
            ("BACKEND_PUBLIC_URL", self.BACKEND_PUBLIC_URL),
            ("TELEGRAM_MINI_APP_BASE_URL", self.TELEGRAM_MINI_APP_BASE_URL),
        ):
            parsed = urlparse(value)
            if parsed.scheme != "https" or not parsed.netloc:
                errors.append(f"{name} must be a valid HTTPS URL")
            if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
                errors.append(f"{name} must not point to localhost")
        if urlparse(self.TELEGRAM_MINI_APP_BASE_URL).hostname not in {"t.me", "telegram.me"}:
            errors.append("TELEGRAM_MINI_APP_BASE_URL must use a Telegram t.me URL")

        origins = self.cors_allowed_origins
        if not origins:
            errors.append("CORS_ALLOWED_ORIGINS must contain at least one origin")
        for origin in origins:
            parsed = urlparse(origin)
            if origin == "*":
                errors.append("CORS_ALLOWED_ORIGINS must not contain wildcard '*'")
            elif parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
                errors.append("CORS_ALLOWED_ORIGINS must not contain localhost")
            elif parsed.scheme != "https" or not parsed.netloc:
                errors.append("CORS_ALLOWED_ORIGINS entries must be valid HTTPS origins")

        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

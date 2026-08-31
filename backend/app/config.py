from typing import Optional
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
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

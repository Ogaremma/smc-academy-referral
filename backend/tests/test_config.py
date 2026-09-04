import pytest

from app.config import Settings


def production_settings(**overrides):
    values = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "s" * 32,
        "WEBHOOK_SECRET": "w" * 32,
        "BOT_TOKEN": "123:token",
        "DATABASE_URL": "postgresql+asyncpg://user:pass@db.example.com/app",
        "FRONTEND_URL": "https://app.example.com",
        "BACKEND_PUBLIC_URL": "https://api.example.com",
        "CORS_ALLOWED_ORIGINS": "https://app.example.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_valid_production_configuration():
    production_settings().validate_production()


def test_production_configuration_accepts_vercel_frontend_origin():
    """The deployed Mini App origin must be a valid explicit CORS origin."""
    production_settings(
        FRONTEND_URL="https://smc-academy-referral.vercel.app",
        CORS_ALLOWED_ORIGINS="https://smc-academy-referral.vercel.app",
    ).validate_production()


@pytest.mark.parametrize(
    "override, expected",
    [
        ({"BOT_TOKEN": ""}, "BOT_TOKEN"),
        ({"SECRET_KEY": "short"}, "SECRET_KEY"),
        ({"WEBHOOK_SECRET": "short"}, "WEBHOOK_SECRET"),
        ({"DATABASE_URL": "sqlite+aiosqlite:///./app.db"}, "SQLite"),
        ({"FRONTEND_URL": "http://localhost:5173"}, "FRONTEND_URL"),
        ({"BACKEND_PUBLIC_URL": "http://api.example.com"}, "BACKEND_PUBLIC_URL"),
        ({"CORS_ALLOWED_ORIGINS": "*"}, "wildcard"),
        ({"CORS_ALLOWED_ORIGINS": "http://localhost:5173"}, "localhost"),
    ],
)
def test_invalid_production_configuration(override, expected):
    with pytest.raises(ValueError, match=expected):
        production_settings(**override).validate_production()


def test_development_configuration_keeps_local_defaults_usable():
    Settings(
        _env_file=None,
        ENVIRONMENT="development",
        SECRET_KEY="s" * 32,
        WEBHOOK_SECRET="w" * 32,
    ).validate_production()

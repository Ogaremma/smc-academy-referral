import sqlite3

from alembic import command
from alembic.config import Config

from app.config import settings


def test_alembic_initial_migration_creates_schema(tmp_path, monkeypatch):
    database_path = tmp_path / "migration_test.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}")

    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.check(config)

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        referral_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(referrals)")
        }
        referral_schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'referrals'"
        ).fetchone()[0]

        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO users (telegram_id, is_active) VALUES (?, ?)",
            (1, True),
        )
        connection.execute(
            "INSERT INTO referral_codes (user_id, code, is_active) VALUES (?, ?, ?)",
            (1, "TESTCODE", True),
        )

        try:
            connection.execute(
                """
                INSERT INTO referrals (
                    referral_code_id, referrer_id, google_form_response_id, status
                ) VALUES (?, ?, ?, ?)
                """,
                (1, 1, "invalid-status-response", "invalid"),
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("referral status check constraint was not enforced")

    assert {"users", "referral_codes", "referrals", "webhook_logs", "alembic_version"} <= tables
    assert "google_form_response_id" in referral_columns
    assert "registered_at" in referral_columns
    assert "ck_referrals_status" in referral_schema

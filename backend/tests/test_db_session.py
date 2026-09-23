"""Pooled connections must be validated before a request uses one.

The production database is PostgreSQL and the server closes an idle pooled
connection. Without pre-ping the first request after an idle period is handed
the dead connection and fails with an unhandled OperationalError (HTTP 500) -
which is exactly the diagnostics call that opens a recovery run.
"""
from app.db.session import build_engine_kwargs


def test_sqlite_engine_keeps_the_thread_flag_only():
    kwargs = build_engine_kwargs("sqlite+aiosqlite:///./smc_referral.db")
    assert kwargs == {"connect_args": {"check_same_thread": False}}


def test_postgres_engine_pre_pings_and_recycles_idle_connections():
    kwargs = build_engine_kwargs("postgresql+asyncpg://user:pass@db.example.com/app")
    assert kwargs["pool_pre_ping"] is True
    assert kwargs["pool_recycle"] > 0

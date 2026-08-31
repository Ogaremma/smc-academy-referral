import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
from typing import AsyncGenerator

# Ensure backend directory is in sys.path for importing app modules in test runner
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Set test configuration overrides
TEST_BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz_TEST_TOKEN"
TEST_WEBHOOK_SECRET = "test_super_secret_webhook_key_123"

settings.BOT_TOKEN = TEST_BOT_TOKEN
settings.WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
settings.SECRET_KEY = "test_jwt_secret_key_for_unit_tests"


def create_telegram_init_data(
    bot_token: str = TEST_BOT_TOKEN,
    user_dict: dict = None,
    auth_date: int = None,
    tamper_hash: bool = False,
    omit_hash: bool = False,
) -> str:
    """Helper to generate cryptographically valid Telegram initData query strings."""
    if user_dict is None:
        user_dict = {
            "id": 987654321,
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
        }

    if auth_date is None:
        auth_date = int(time.time())

    user_json = json.dumps(user_dict, separators=(",", ":"))
    params = {
        "auth_date": str(auth_date),
        "user": user_json,
    }

    sorted_items = sorted(params.items(), key=lambda x: x[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_items)

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if tamper_hash:
        calculated_hash = "deadbeef1234567890abcdefdeadbeef1234567890abcdefdeadbeef12345678"

    encoded_user = urllib.parse.quote(user_json)

    if omit_hash:
        return f"auth_date={auth_date}&user={encoded_user}"

    return f"auth_date={auth_date}&user={encoded_user}&hash={calculated_hash}"


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

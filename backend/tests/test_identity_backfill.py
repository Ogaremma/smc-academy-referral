"""Admin-only Telegram profile refresh for accounts stored as numeric ids.

Telegram is the only source of profile data: the Bot API getChat result is
persisted as-is, and a chat Telegram cannot resolve keeps the numeric fallback
instead of inventing an identity.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.models import User
from app.services import identity_service

REFRESH_ALL = "/api/v1/admin/telegram/refresh-profiles"


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


NOT_FOUND = _FakeResponse(400, {"ok": False, "description": "Bad Request: chat not found"})


class _FakeAsyncClient:
    """Stand-in for httpx.AsyncClient that answers getChat from a script."""

    responses: dict[int, _FakeResponse] = {}
    requested: list[int] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def post(self, url: str, json: dict | None = None) -> _FakeResponse:
        chat_id = json["chat_id"]
        _FakeAsyncClient.requested.append(chat_id)
        return _FakeAsyncClient.responses.get(chat_id, NOT_FOUND)


@pytest.fixture
def fake_telegram(monkeypatch):
    _FakeAsyncClient.responses = {}
    _FakeAsyncClient.requested = []
    monkeypatch.setattr(identity_service.httpx, "AsyncClient", _FakeAsyncClient)
    return _FakeAsyncClient


async def _admin_headers(db_session: AsyncSession) -> dict[str, str]:
    admin = User(telegram_id=809300, username="identity_admin", is_admin=True)
    db_session.add(admin)
    await db_session.commit()
    return {
        "Authorization": f"Bearer {create_access_token({'sub': str(admin.id), 'telegram_id': admin.telegram_id})}"
    }


@pytest.mark.asyncio
async def test_admin_refreshes_a_single_affiliate_profile(
    client: AsyncClient, db_session: AsyncSession, fake_telegram
):
    target = User(telegram_id=700100, is_active=True, account_status="ACTIVE")
    db_session.add(target)
    await db_session.commit()
    fake_telegram.responses[700100] = _FakeResponse(
        200,
        {
            "ok": True,
            "result": {
                "id": 700100,
                "type": "private",
                "first_name": "Ada",
                "last_name": "Obi",
                "username": "ada_obi",
            },
        },
    )

    response = await client.post(
        f"/api/v1/admin/affiliates/{target.id}/refresh-telegram",
        headers=await _admin_headers(db_session),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["refreshed"] is True
    assert body["username"] == "ada_obi"
    assert body["first_name"] == "Ada"
    assert fake_telegram.requested == [700100]


@pytest.mark.asyncio
async def test_unresolvable_chat_keeps_the_numeric_fallback(
    client: AsyncClient, db_session: AsyncSession, fake_telegram
):
    target = User(telegram_id=700101, is_active=True, account_status="ACTIVE")
    db_session.add(target)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/admin/affiliates/{target.id}/refresh-telegram",
        headers=await _admin_headers(db_session),
    )

    assert response.status_code == 404
    assert "chat not found" in response.json()["detail"]
    stored = (
        await db_session.execute(select(User).where(User.id == target.id))
    ).scalar_one()
    assert stored.username is None
    assert stored.first_name is None
    assert stored.last_name is None


@pytest.mark.asyncio
async def test_bulk_refresh_only_targets_accounts_without_a_profile(
    client: AsyncClient, db_session: AsyncSession, fake_telegram
):
    named = User(
        telegram_id=700200,
        username="already_known",
        first_name="Known",
        is_active=True,
        account_status="ACTIVE",
    )
    missing = User(telegram_id=700201, is_active=True, account_status="ACTIVE")
    db_session.add_all([named, missing])
    await db_session.commit()
    fake_telegram.responses[700201] = _FakeResponse(
        200,
        {"ok": True, "result": {"id": 700201, "first_name": "Fresh", "username": "fresh_name"}},
    )
    headers = await _admin_headers(db_session)

    preview = await client.post(REFRESH_ALL, headers=headers, json={"dry_run": True})
    assert preview.status_code == 200, preview.text
    assert preview.json()["checked"] == 1
    assert preview.json()["refreshed"] == 1
    assert 700200 not in fake_telegram.requested
    stored_missing = (
        await db_session.execute(select(User).where(User.id == missing.id))
    ).scalar_one()
    assert stored_missing.username is None

    applied = await client.post(REFRESH_ALL, headers=headers, json={})
    assert applied.status_code == 200, applied.text
    assert applied.json()["refreshed"] == 1
    assert stored_missing.username == "fresh_name"
    assert stored_missing.first_name == "Fresh"


@pytest.mark.asyncio
async def test_refresh_endpoints_are_admin_only(
    client: AsyncClient, db_session: AsyncSession, fake_telegram
):
    affiliate = User(
        telegram_id=700300,
        username="plain_user",
        is_active=True,
        account_status="ACTIVE",
    )
    db_session.add(affiliate)
    await db_session.commit()
    headers = {
        "Authorization": f"Bearer {create_access_token({'sub': str(affiliate.id), 'telegram_id': affiliate.telegram_id})}"
    }

    assert (
        await client.post(REFRESH_ALL, headers=headers, json={})
    ).status_code == 403
    assert (
        await client.post(
            f"/api/v1/admin/affiliates/{affiliate.id}/refresh-telegram",
            headers=headers,
        )
    ).status_code == 403
    assert fake_telegram.requested == []
